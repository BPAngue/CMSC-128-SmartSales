from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from .models import Product
from .models import Transaction
from django.contrib.auth.password_validation import validate_password
import re

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'business_name']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered. Please use a different one.")
        return email

# Step 1: Form for requesting password reset (email input)
class EmailRequestForm(forms.Form):
    email = forms.EmailField(
        max_length=254, 
        widget=forms.EmailInput(attrs={
            'class': 'input-field',
            'placeholder': 'Enter your email'
        })
    )

# Step 2: Form for entering the 6-digit OTP
class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'input-field',
            'placeholder': 'Enter the 6-digit code'
        })
    )

# Step 3: Form for setting new password
class PasswordResetForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input-field',
            'placeholder': "Enter your new password"
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        validate_password(password)

        return cleaned_data
    
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['customer_name', 'customer_phone', 'product', 'quantity']

    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(stock__gt=0)

    def clean_customer_phone(self):
        phone = self.cleaned_data.get('customer_phone')
        if phone:
            # Validate PH phone formats: 09XXXXXXXXX or +639XXXXXXXXX
            if not re.match(r'^(09\d{9}|\+639\d{9})$', phone):
                raise forms.ValidationError(
                    "Enter a valid Philippine phone number (e.g., 09123456789 or +639123456789)."
                )
        return phone

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')

        if product and quantity and product.stock < quantity:
            raise forms.ValidationError(
                f"Insufficient stock for {product.name}. Only {product.stock} left."
            )
        return cleaned_data 