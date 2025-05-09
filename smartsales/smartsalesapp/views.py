from django.shortcuts import render, HttpResponse, redirect, get_object_or_404
from django.core.paginator import Paginator
from .forms import CustomUserCreationForm, EmailRequestForm, OTPVerificationForm, PasswordResetForm, TransactionForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PasswordResetCode
from .models import Product
from .models import Transaction
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