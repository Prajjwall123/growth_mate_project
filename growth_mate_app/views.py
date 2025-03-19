from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .models import UserProfile

def home(request):
    return render(request,"index.html")

def signup(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered, try another email.")
            return redirect("signup")

        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect("signup")

        user = User.objects.create_user(username=email, email=email, password=password1)
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        UserProfile.objects.create(user=user)

        messages.success(request, "Account created successfully! You can now log in.")
        return redirect("login")

    return render(request, "signup.html")


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request, "Invalid login credentials, please try again.")
            return redirect("login")

        login(request, user)
        messages.success(request, "Login successful!")
        return redirect("home") 

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")
