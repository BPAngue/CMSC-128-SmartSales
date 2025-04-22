from django.shortcuts import render, HttpResponse, redirect
from .forms import CustomUserCreationForm, EmailRequestForm, OTPVerificationForm, PasswordResetForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PasswordResetCode
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.views.decorators.cache import never_cache
import random

@login_required
def home(request):
    return render(request, "home.html")

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