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
from .utils import prepare_sales_dataframe, arima_forecast, growth_pct, get_date_range, calculate_sales_data
import pandas as pd
import random
import json

@login_required
def home(request):
    period = request.GET.get('period', 'monthly')
    actual_sales, top_product = calculate_sales_data(period)

    start_date, _ = get_date_range(period)
    transactions_qs = Transaction.objects.filter(date_of_transaction__gte=start_date)
    df = prepare_sales_dataframe(transactions_qs)

    forecasts = {}
    accuracy = 0

    if df is not None:
        for p, steps in {'daily': 1, 'weekly': 7, 'monthly': 30}.items():
            forecast_series, _, acc = arima_forecast(df['total_sales'], steps=steps)
            forecasts[p] = forecast_series.sum()
            accuracy = acc  # Use latest accuracy or compute separately if needed

        request.session['forecast_sales'] = forecasts
        request.session['forecast_accuracy'] = float(accuracy)
    else:
        request.session['forecast_sales'] = {'daily': 0.0, 'weekly': 0.0, 'monthly': 0.0}
        request.session['forecast_accuracy'] = 0.0

    context = {
        'period': period,
        'actual_sales': f"{actual_sales:,.2f}",
        'forecast_sales': f"{forecasts.get(period, 0):,.2f}",
        'model_accuracy': accuracy,
        'top_product': top_product,
        'confidence_level': 95,
        'transactions': transactions_qs.order_by('-date_of_transaction')[:5],
        'insufficient_data': df is None or len(df) < 5,
    }

    return render(request, 'dashboard.html', context)

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
    period = request.GET.get('period', 'monthly')
    today = timezone.now().date()

    # Current Period Sales Data
    daily_sales, _ = calculate_sales_data('daily')
    weekly_sales, _ = calculate_sales_data('weekly')
    monthly_sales, _ = calculate_sales_data('monthly')

    # Previous Period Data for Growth Calculation
    yesterday = today - timedelta(days=1)
    last_week_start = today - timedelta(days=today.weekday() + 7)
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

    yesterday_sales = Transaction.objects.filter(date_of_transaction=yesterday).aggregate(total=Sum('total_amount'))['total'] or 0
    last_week_sales = Transaction.objects.filter(date_of_transaction__gte=last_week_start, date_of_transaction__lt=today - timedelta(days=today.weekday())).aggregate(total=Sum('total_amount'))['total'] or 0
    last_month_sales = Transaction.objects.filter(date_of_transaction__gte=last_month_start, date_of_transaction__lt=today.replace(day=1)).aggregate(total=Sum('total_amount'))['total'] or 0

    daily_growth = growth_pct(daily_sales, yesterday_sales)
    weekly_growth = growth_pct(weekly_sales, last_week_sales)
    monthly_growth = growth_pct(monthly_sales, last_month_sales)

    # Prepare Chart Data
    def prepare_chart_data(trunc_func):
        trend = (Transaction.objects
                 .annotate(period=trunc_func('date_of_transaction'))
                 .values('period')
                 .annotate(total=Sum('total_amount'))
                 .order_by('period'))
        labels = [str(entry['period']) for entry in trend]
        data = [float(entry['total']) for entry in trend]
        return labels, data

    daily_labels, daily_data = prepare_chart_data(TruncDate)
    weekly_labels, weekly_data = prepare_chart_data(TruncWeek)
    monthly_labels, monthly_data = prepare_chart_data(TruncMonth)

    # Properly Filter Top Products Based on Selected Period
    start_date, end_date = get_date_range(period)
    top_products_qs = (Transaction.objects
                       .filter(date_of_transaction__range=[start_date, end_date])
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
        'daily_labels': json.dumps(daily_labels, cls=DjangoJSONEncoder),
        'daily_data': json.dumps(daily_data, cls=DjangoJSONEncoder),
        'weekly_labels': json.dumps(weekly_labels, cls=DjangoJSONEncoder),
        'weekly_data': json.dumps(weekly_data, cls=DjangoJSONEncoder),
        'monthly_labels': json.dumps(monthly_labels, cls=DjangoJSONEncoder),
        'monthly_data': json.dumps(monthly_data, cls=DjangoJSONEncoder),
        'period': period,
        'top_products': [{'name': p['product__name'], 'total_sold': p['total_sold']} for p in top_products_qs],
        'insufficient_data': False,
    }

    return render(request, 'analytics.html', context)

@login_required
def forecast_view(request):
    forecasts = request.session.get('forecast_sales', {'daily': 0.0, 'weekly': 0.0, 'monthly': 0.0})
    model_accuracy = request.session.get('forecast_accuracy', 0.0)

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)

    # Get historical data for comparison
    df = prepare_sales_dataframe(Transaction.objects.all())
    actual_today = df['total_sales'].get(str(pd.Timestamp(today)), 0.0) if df is not None else 0.0
    actual_yesterday = df['total_sales'].get(str(pd.Timestamp(yesterday)), 0.0) if df is not None else 0.0
    actual_last_week = df['total_sales'].get(str(pd.Timestamp(last_week)), 0.0) if df is not None else 0.0
    actual_last_month = df['total_sales'].get(str(pd.Timestamp(last_month)), 0.0) if df is not None else 0.0

    # Growth Calculations
    daily_growth = growth_pct(forecasts.get('daily', 0.0), actual_yesterday)
    weekly_growth = growth_pct(forecasts.get('weekly', 0.0), actual_last_week)
    monthly_growth = growth_pct(forecasts.get('monthly', 0.0), actual_last_month)

    # Prepare data for the chart (actual vs forecasted)
    forecast_chart_data = json.dumps({
        'day': [actual_yesterday, forecasts.get('daily', 0.0)],
        'week': [actual_last_week, forecasts.get('weekly', 0.0)],
        'month': [actual_last_month, forecasts.get('monthly', 0.0)],
    }, cls=DjangoJSONEncoder)

    context = {
        'next_day_forecast': f"{forecasts.get('daily', 0.0):,.2f}",
        'weekly_forecast': f"{forecasts.get('weekly', 0.0):,.2f}",
        'monthly_forecast': f"{forecasts.get('monthly', 0.0):,.2f}",
        'daily_growth': daily_growth,
        'weekly_growth': weekly_growth,
        'monthly_growth': monthly_growth,
        'confidence_level': 95,
        'model_accuracy': model_accuracy,
        'last_updated': timezone.now().strftime("%B %d, %Y %I:%M %p"),
        'forecast_chart_data': forecast_chart_data,
        'insufficient_data': all(value == 0 for value in forecasts.values()),
    }

    return render(request, 'forecast.html', context)
