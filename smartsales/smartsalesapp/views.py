from django.shortcuts import render, HttpResponse, redirect, get_object_or_404
from django.core.paginator import Paginator
from .forms import CustomUserCreationForm, EmailRequestForm, OTPVerificationForm, PasswordResetForm, TransactionForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PasswordResetCode
from .models import Product
from .models import Transaction
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from datetime import timedelta
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
import random
import json

@login_required
def home(request):
    transactions = Transaction.objects.all().order_by('-date_of_transaction')[:10]  # Latest 10 transactions
    return render(request, "dashboard.html", {'transactions': transactions})

def authView(request):
    form = CustomUserCreationForm()
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully.")
            return redirect("login")
    return render(request, "registration/signup.html", {"form": form})

# for password reset
User = get_user_model()

@never_cache
def request_reset(request):
    if request.session.get("email_sent"):
        return redirect("verify_otp")
    
    form = EmailRequestForm()

    if request.method == "POST":
        form = EmailRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            
            try:
                user = User.objects.get(email=email)
                code = f"{random.randint(100000, 999999)}"
                PasswordResetCode.objects.create(user=user, code=code)

                send_mail(
                    subject="SmartSales Password Reset Code",
                    message=f"Your SmartSales verification code is: {code}",
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=False,
                )

                request.session["reset_email"] = email
                request.session["email_sent"] = True
                messages.success(request, "Email sent successfully!")
                return redirect("verify_otp")
            
            except User.DoesNotExist:
                form.add_error("email", "No user with this email exists.")

    return render(request, "registration/request_reset.html", {"form": form})

@never_cache
def verify_otp(request):
    if request.session.get("otp_verified"):
        return redirect("set_new_password")
    
    form = OTPVerificationForm()

    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            code_input = form.cleaned_data["otp"]
            email = request.session.get("reset_email")

            try:
                user = User.objects.get(email=email)
                otp = PasswordResetCode.objects.filter(user=user, code=code_input, is_used=False).latest("created_at")

                if otp.is_expired():
                    form.add_error("otp", "This code has expired. Please request a new one.")
                    return render(request, "registration/verify_otp.html", {"form": form})
                
                otp.is_used = True
                otp.save()
                request.session["verified_user_id"] = user.id
                request.session["otp_verified"] = True
                return redirect("set_new_password")
            
            except (User.DoesNotExist, PasswordResetCode.DoesNotExist):
                form.add_error("otp", "Invalid code.")

    return render(request, "registration/verify_otp.html", {"form": form})

def set_new_password(request):
    user_id = request.session.get("verified_user_id")

    if not user_id:
        return redirect("login")
    
    form = PasswordResetForm()

    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["password"]
            user = User.objects.get(id=user_id)
            user.password = make_password(new_password)
            user.save()

            del request.session["verified_user_id"]
            del request.session["otp_verified"]
            messages.success(request, "Password reset successful. Please login")
            return redirect("login")
        
    return render(request, "registration/set_new_password.html", {"form": form})

def resend_otp(request):
    email = request.session.get("reset_email")
    if email:
        try:
            user = User.objects.get(email=email)
            code = f"{random.randint(100000, 999999)}"
            PasswordResetCode.objects.create(user=user, code=code)

            send_mail(
                subject="Your new SmartSales verification code",
                message=f"Here is your new verification code: {code}",
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, "A new verification code has been sent to your email.")

        except User.DoesNotExist:
            messages.error(request, "Unable to resend code. Please try again.")

    return redirect("verify_otp")

def products_view(request):
    # fetch filter values from the GET request
    status_filter = request.GET.get('status', '')
    product_filter = request.GET.get('product', '')

    # Queryset filtering logic
    products = Product.objects.all().order_by('id')
    if status_filter and status_filter != 'Status':
        products = products.filter(status__iexact=status_filter)
    if product_filter and product_filter != 'Product':
        products = products.filter(name__icontains=product_filter)

    # pagination: 10 products per page
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'current_status': status_filter,
        'current_product': product_filter,
    }

    return render(request, 'products.html', context)

def add_product_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        stock = request.POST.get('stock')

        if not name or not price or not stock:
            messages.error(request, "All fields are required.")
        else:
            try:
                price = float(price)
                stock = int(stock)

                if price < 0 or stock < 0:
                    messages.error(request, "Price and stock must be non-negative.")
                else:
                    status = "Out of Stock" if stock == 0 else "Available"
                    Product.objects.create(name=name, price=price, stock=stock, status=status)
                    messages.success(request, "Product added successfully!")
                    return redirect('products')
            except ValueError:
                messages.error(request, "Invalid input for price or stock.")

    return render(request, 'add_product.html')

def delete_product_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('products')
    return redirect('products')

def edit_product_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        stock = request.POST.get('stock')

        if not name or not price or not stock:
            messages.error(request, "All fields are required.")
        else:
            try:
                price = float(price)
                stock = int(stock)

                if price < 0 or stock < 0:
                    messages.error(request, "Price and stock must be non-negative.")
                else:
                    product.name = name
                    product.price = price
                    product.stock = stock
                    product.status = "Out of Stock" if stock == 0 else "Available"
                    product.save()
                    messages.success(request, "Product updated successfully!")
                    return redirect('products')
            except ValueError:
                messages.error(request, "Invalid input for price or stock.")

    return render(request, 'edit_product.html', {'product': product})

@login_required
def add_transaction_view(request):
    # Only fetch products that have stock > 0
    products = Product.objects.filter(stock__gt=0)
    products_json = json.dumps(
        list(products.values('id', 'name', 'price', 'stock')), 
        cls=DjangoJSONEncoder
    )

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        customer_phone = request.POST.get('customer_phone')
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity'))
        date_of_transaction = request.POST.get('date_of_transaction') or timezone.now().date()

        product = Product.objects.get(id=product_id)

        if product.stock < quantity:
            messages.error(request, f"Insufficient stock for {product.name}. Only {product.stock} left.")
            return redirect('record_transaction')

        total_amount = product.price * quantity

        # Save transaction
        Transaction.objects.create(
            customer_name=customer_name,
            customer_phone=customer_phone,
            product=product,
            quantity=quantity,
            total_amount=total_amount,
            date_of_transaction=date_of_transaction
        )

        # Update product stock
        product.stock -= quantity
        if product.stock == 0:
            product.status = "Out of Stock"
        product.save()

        messages.success(request, "Transaction recorded successfully!")
        return redirect('home')

    context = {
        'products': products,
        'products_json': products_json,
        'today_date': timezone.now().date(),
    }
    return render(request, 'record_transaction.html', context)

@login_required
def recent_transactions_view(request):
    transactions = Transaction.objects.all().order_by('-date_of_transaction')[:10]  # Last 10 transactions
    return render(request, 'dashboard.html', {'transactions': transactions})

@login_required
def transactions_list_view(request):
    # Filters from GET parameters
    date_filter = request.GET.get('date', '')
    product_filter = request.GET.get('product', '')

    transactions = Transaction.objects.all().order_by('-date_of_transaction')
    products = Product.objects.all()

    # Apply filters if provided
    if date_filter:
        transactions = transactions.filter(date_of_transaction=date_filter)
    if product_filter:
        transactions = transactions.filter(product__name__icontains=product_filter)

    # Pagination: 10 transactions per page
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'transactions': page_obj,
        'products': products,
        'current_date': date_filter,
        'current_product': product_filter,
    }
    return render(request, 'transactions.html', context)

@login_required
def analytics_view(request):
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_last_week = start_of_week - timedelta(days=7)
    start_of_month = today.replace(day=1)
    start_of_last_month = (start_of_month - timedelta(days=1)).replace(day=1)

    # Current Period Sales
    daily_sales = Transaction.objects.filter(date_of_transaction=today).aggregate(total=Sum('total_amount'))['total'] or 0
    weekly_sales = Transaction.objects.filter(date_of_transaction__gte=start_of_week).aggregate(total=Sum('total_amount'))['total'] or 0
    monthly_sales = Transaction.objects.filter(date_of_transaction__gte=start_of_month).aggregate(total=Sum('total_amount'))['total'] or 0

    # Previous Period Sales
    yesterday = today - timedelta(days=1)
    yesterday_sales = Transaction.objects.filter(date_of_transaction=yesterday).aggregate(total=Sum('total_amount'))['total'] or 0

    last_week_sales = Transaction.objects.filter(
        date_of_transaction__gte=start_of_last_week,
        date_of_transaction__lt=start_of_week
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    last_month_sales = Transaction.objects.filter(
        date_of_transaction__gte=start_of_last_month,
        date_of_transaction__lt=start_of_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Growth Calculations
    def calculate_growth(current, previous):
        if previous > 0:
            return round(((current - previous) / previous) * 100, 2)
        return 0

    daily_growth = calculate_growth(daily_sales, yesterday_sales)
    weekly_growth = calculate_growth(weekly_sales, last_week_sales)
    monthly_growth = calculate_growth(monthly_sales, last_month_sales)

    # Revenue Data for Chart.js
    def get_revenue_data(group_by):
        if group_by == 'daily':
            trunc = TruncDate('date_of_transaction')
            range_days = 7
        elif group_by == 'weekly':
            trunc = TruncWeek('date_of_transaction')
            range_days = 30
        else:
            trunc = TruncMonth('date_of_transaction')
            range_days = 365

        trend = (Transaction.objects
            .filter(date_of_transaction__gte=today - timedelta(days=range_days))
            .annotate(period=trunc)
            .values('period')
            .annotate(total=Sum('total_amount'))
            .order_by('period'))

        labels = [str(entry['period']) for entry in trend]
        data = [float(entry['total']) for entry in trend]
        return labels, data

    daily_labels, daily_data = get_revenue_data('daily')
    weekly_labels, weekly_data = get_revenue_data('weekly')
    monthly_labels, monthly_data = get_revenue_data('monthly')

    # Top 5 Best Selling Products
    period = request.GET.get('period', 'monthly')
    if period == 'daily':
        date_filter = today
    elif period == 'weekly':
        date_filter = start_of_week
    else:
        date_filter = start_of_month

    top_products = (Transaction.objects
        .filter(date_of_transaction__gte=date_filter)
        .values('product__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5])

    context = {
        'daily_sales': f"{daily_sales:,.2f}",
        'weekly_sales': f"{weekly_sales:,.2f}",
        'monthly_sales': f"{monthly_sales:,.2f}",
        'daily_growth': daily_growth,
        'weekly_growth': weekly_growth,
        'monthly_growth': monthly_growth,
        'top_products': [{'name': p['product__name'], 'total_sold': p['total_sold']} for p in top_products],
        'daily_labels': json.dumps(daily_labels),
        'daily_data': json.dumps(daily_data),
        'weekly_labels': json.dumps(weekly_labels),
        'weekly_data': json.dumps(weekly_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_data': json.dumps(monthly_data),
        'period': period,
    }

    return render(request, 'analytics.html', context)