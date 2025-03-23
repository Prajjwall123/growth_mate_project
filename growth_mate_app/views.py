from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
import random
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Course, UserProfile
from .tokens import generate_token  
from growth_mate_project import settings 
from django.http import JsonResponse
from django.core.mail import send_mail
import random
from django.contrib.auth.decorators import login_required
from django.db.models import Count


otp_storage = {}

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

        otp = str(random.randint(100000, 999999))
        otp_storage[email] = otp  

        email_subject = "Your OTP for Email Verification"
        email_message = f"Hello {first_name},\n\nYour One-Time Password (OTP) for verification is: {otp}\n\nEnter this OTP on the website to activate your account.\n\nThank you!"
        send_mail(email_subject, email_message, settings.EMAIL_HOST_USER, [email], fail_silently=True)

        request.session['temp_user_data'] = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': password1,
            'role': role
        }

        messages.success(request, "An OTP has been sent to your email. Please enter it to verify your account.")
        return redirect("verify_otp")

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
        
        # Check user role and redirect accordingly
        try:
            user_profile = UserProfile.objects.get(user=user)
            if user_profile.role == 'manager':
                return redirect('manager_dashboard')
            else:
                return redirect('home')
        except UserProfile.DoesNotExist:
            return redirect('home')

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")

def verify_otp(request):
    if request.method == "POST":
        email = request.session.get('temp_user_data', {}).get('email')
        entered_otp = request.POST.get("otp")

        if not email or email not in otp_storage:
            messages.error(request, "Session expired. Please register again.")
            return redirect("signup")

        if otp_storage[email] == entered_otp:
            user_data = request.session.get('temp_user_data')

            user = User.objects.create_user(username=email, email=email, password=user_data['password'])
            user.first_name = user_data['first_name']
            user.last_name = user_data['last_name']
            user.is_active = True 
            user.save()

            UserProfile.objects.create(user=user, role=user_data['role'])

            del otp_storage[email]
            request.session.pop('temp_user_data', None)

            messages.success(request, "Your account has been activated! You can now log in.")
            return redirect("login")
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("verify_otp")

    return render(request, "verify_otp.html")


def resend_otp(request):
    if request.method == "POST":
        new_otp = random.randint(100000, 999999)  

        request.session['otp'] = new_otp  

        send_mail(
            "Your New OTP",
            f"Your OTP code is: {new_otp}",
            "no-reply@growthmate.com",
            [request.user.email], 
            fail_silently=False,
        )

        return JsonResponse({"message": "OTP has been resent!", "success": True})
    return JsonResponse({"message": "Invalid request", "success": False}, status=400)

def my_courses_view(request):
    trending_courses = Course.objects.all().order_by('-due_date')[:6]
    return render(request, "my_courses.html", {"trending_courses": trending_courses})

@login_required
def manager_dashboard(request):
    # Check if the user is a manager
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'manager':
            messages.error(request, "Access denied. Manager privileges required.")
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect('home')

    # Get courses created by the manager
    manager_courses = Course.objects.filter(uploaded_by=request.user)
    
    # Calculate statistics
    total_courses = manager_courses.count()
    active_courses = manager_courses.filter(is_active=True).count()
    total_enrollments = sum(course.enrollment_set.count() for course in manager_courses)
    
    # Get recent activities (last 5)
    recent_activities = manager_courses.order_by('-created_at')[:5]
    
    context = {
        'user_profile': user_profile,
        'total_courses': total_courses,
        'active_courses': active_courses,
        'total_enrollments': total_enrollments,
        'recent_activities': recent_activities,
        'courses': manager_courses[:5],  # Show only 5 courses
    }
    
    return render(request, 'manager_dashboard.html', context)