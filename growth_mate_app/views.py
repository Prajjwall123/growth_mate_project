from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import UserProfile
from .tokens import generate_token  
from growth_mate_project import settings 

def signup(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        role = request.POST.get("role")  
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if role not in ["manager", "employee"]:
            messages.error(request, "Invalid role selection.")
            return redirect("signup")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered, try another email.")
            return redirect("signup")

        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect("signup")

        user = User.objects.create_user(username=email, email=email, password=password1)
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = False 
        user.save()

        UserProfile.objects.create(user=user, role=role)

        current_site = get_current_site(request)
        email_subject = "Confirm your Email - MyProject"
        email_message = render_to_string("email_verification.html", {
            "name": user.first_name,
            "domain": current_site.domain,
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": generate_token.make_token(user)
        })
        email = EmailMessage(
            email_subject,
            email_message,
            settings.EMAIL_HOST_USER,
            [user.email],
        )
        email.fail_silently = True
        email.send()

        messages.success(request, "We have sent you a confirmation email. Please check your inbox.")
        return redirect("login")

    return render(request, "signup.html")

def home(request):
    return render(request, "index.html")

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

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and generate_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Your account has been activated! You can now log in.")
        return redirect("login")
    else:
        return render(request, "activation_failed.html")
