from django.shortcuts import render, HttpResponse, redirect
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

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