from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Create your models here.

class CustomUser(AbstractUser):
    business_name = models.CharField(max_length=100, blank=False)

    def __str__(self):
        return self.username
    
class PasswordResetCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.code}"

    def is_expired(self):
        return (timezone.now() - self.created_at).seconds > 600
    
class Product(models.Model):
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Out of Stock', 'Out of Stock'),
    ]

    name = models.CharField(max_length=255)
    stock = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.name}"
    
class Transaction(models.Model):
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=15, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_of_transaction = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Order {self.id} - {self.customer_name}"