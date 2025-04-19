from django.shortcuts import render, HttpResponse, redirect
from .models import TodoItem
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Create your views here.
@login_required
def home(request):
    return render(request, "home.html")

def todos(request):
    items = TodoItem.objects.all()
    return render(request, "todos.html", {"todos": items})

def authView(request):
    form = UserCreationForm()

    if request.method == "POST":
        form = UserCreationForm(request.POST or None)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully.")
            return redirect("login")
        else:
            form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})