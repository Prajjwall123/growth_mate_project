import string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
import random
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Course, UserProfile, Lesson
from .tokens import generate_token  
from growth_mate_project import settings 
from django.http import JsonResponse
from django.core.mail import send_mail
import random
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from social_django.utils import load_strategy, load_backend
from social_core.backends.oauth import BaseOAuth2PKCE
from social_core.exceptions import MissingBackend


otp_storage = {}

def signup(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        role = request.POST.get("role")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("signup")

        # Create user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Create user profile
        UserProfile.objects.create(
            user=user,
            role=role,
            email=email,
            first_name=first_name,
            last_name=last_name
        )

        # Generate and send OTP
        otp = ''.join(random.choices(string.digits, k=6))
        user_profile = UserProfile.objects.get(user=user)
        user_profile.otp = otp
        user_profile.otp_created_at = timezone.now()
        user_profile.save()

        send_mail(
            'Verify your email',
            f'Your OTP is: {otp}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        messages.success(request, "Registration successful! Please check your email for OTP verification.")
        return redirect("verify_otp")

    return render(request, "signup.html")

def home(request):
    context = {}
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            context['user_profile'] = user_profile
        except UserProfile.DoesNotExist:
            pass
    return render(request, "index.html", context)

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
            elif user_profile.role == 'employee':
                return redirect('employee_dashboard')
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

    # Static data for dashboard
    context = {
        'user_profile': user_profile,
        'total_users': 324,
        'total_courses': 98,
        'active_courses': 92,
        'top_students': [
            {'name': 'Uttam Shrestha', 'progress': 95},
            {'name': 'Nisha Khadka', 'progress': 40},
            {'name': 'Simran KC', 'progress': 50},
            {'name': 'Sarah Johnson', 'progress': 85}
        ],
        'course_completion': [
            {'title': 'Health Science', 'progress': 70, 'total': 100},
            {'title': 'Fitness', 'progress': 40, 'total': 100},
            {'title': 'Sports Management', 'progress': 50, 'total': 100}
        ]
    }
    
    return render(request, 'manager/dashboard.html', context)

@login_required
def my_courses(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    if user_profile.role == 'manager':
        courses = Course.objects.filter(uploaded_by=request.user).order_by('-created_at')
    else:  # employee
        courses = Course.objects.filter(enrolled_users=request.user).order_by('-created_at')
    
    return render(request, 'my_courses.html', {
        'courses': courses,
        'user_profile': user_profile
    })

@login_required
@require_POST
def add_course(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'manager':
        messages.error(request, 'Access denied. Managers only.')
        return redirect('home')
    
    try:
        course = Course.objects.create(
            title=request.POST['title'],
            duration=request.POST['duration'],
            due_date=request.POST['due_date'],
            about_this_course=request.POST['about_this_course'],
            uploaded_by=request.user,
            is_active='is_active' in request.POST
        )
        
        if 'image' in request.FILES:
            course.image = request.FILES['image']
            course.save()
            
        messages.success(request, 'Course created successfully!')
        return redirect('manager_courses')
    except Exception as e:
        messages.error(request, f'Error creating course: {str(e)}')
        return redirect('manager_courses')

@login_required
@require_POST
def add_lesson(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'manager':
        messages.error(request, 'Access denied. Managers only.')
        return redirect('home')
    
    course = get_object_or_404(Course, id=request.POST['course_id'], uploaded_by=request.user)
    
    try:
        # Get the highest order number for this course's lessons
        last_order = Lesson.objects.filter(course=course).order_by('-order').first()
        new_order = (last_order.order + 1) if last_order else 1
        
        lesson = Lesson.objects.create(
            course=course,
            title=request.POST['title'],
            content=request.POST['content'],
            duration=request.POST['duration'],
            order=new_order
        )
        
        messages.success(request, 'Lesson added successfully!')
        return redirect('manager_courses')
    except Exception as e:
        messages.error(request, f'Error adding lesson: {str(e)}')
        return redirect('manager_courses')

@login_required
def edit_course(request, course_id):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'manager':
        messages.error(request, 'Access denied. Managers only.')
        return redirect('home')
    
    course = get_object_or_404(Course, id=course_id, uploaded_by=request.user)
    
    if request.method == 'POST':
        try:
            course.title = request.POST['title']
            course.duration = request.POST['duration']
            course.due_date = request.POST['due_date']
            course.about_this_course = request.POST['about_this_course']
            course.is_active = 'is_active' in request.POST
            
            if 'image' in request.FILES:
                course.image = request.FILES['image']
            
            course.save()
            messages.success(request, 'Course updated successfully!')
            return redirect('manager_courses')
        except Exception as e:
            messages.error(request, f'Error updating course: {str(e)}')
            return redirect('manager_courses')
    
    return render(request, 'edit_course.html', {
        'course': course,
        'user_profile': user_profile
    })

@login_required
def view_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = course.lesson_set.all().order_by('order')
    
    return render(request, 'view_course.html', {
        'course': course,
        'lessons': lessons
    })

@login_required
def profile_settings(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        # Handle file uploads
        if 'profile_pic' in request.FILES:
            user_profile.profile_pic = request.FILES['profile_pic']
        if 'cover_image' in request.FILES:
            user_profile.cover_image = request.FILES['cover_image']

        # Update user fields
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.save()

        # Update profile fields
        if user_profile.role == 'manager':
            user_profile.professional_headline = request.POST.get('professional_headline', user_profile.professional_headline)
        user_profile.bio = request.POST.get('bio', user_profile.bio)
        user_profile.phone = request.POST.get('phone', user_profile.phone)
        user_profile.save()

        # Handle password change
        current_password = request.POST.get('current_password')
        if current_password:
            if request.user.check_password(current_password):
                # For employees, handle complete password change
                if user_profile.role == 'employee':
                    new_password = request.POST.get('new_password')
                    confirm_password = request.POST.get('confirm_password')
                    if new_password and confirm_password:
                        if new_password == confirm_password:
                            request.user.set_password(new_password)
                            request.user.save()
                            messages.success(request, 'Profile and password updated successfully.')
                            # Re-authenticate the user to prevent logout
                            update_session_auth_hash(request, request.user)
                        else:
                            messages.error(request, 'New passwords do not match.')
                    elif new_password or confirm_password:
                        messages.error(request, 'Please provide both new password and confirmation.')
                else:
                    messages.success(request, 'Profile updated successfully.')
            else:
                messages.error(request, 'Current password is incorrect.')
        else:
            messages.success(request, 'Profile updated successfully.')

        return redirect('profile_settings')

    context = {
        'user_profile': user_profile,
    }
    
    # Use different templates based on user role
    if user_profile.role == 'manager':
        return render(request, 'manager/profile_settings.html', context)
    else:
        return render(request, 'employee/profile_settings.html', context)

@login_required
def users_view(request):
    # Check if the user is a manager
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'manager':
            messages.error(request, "Access denied. Manager privileges required.")
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect('home')

    # Static data for users page
    context = {
        'user_profile': user_profile,
        'stats': {
            'total_users': 234,
            'active_users': 136,
            'inactive_users': 98,
            'course_completion': 90
        }
    }
    
    return render(request, 'manager/users.html', context)

@login_required
def courses_view(request):
    # Check if user is a manager
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'manager':
            messages.error(request, 'Access Denied: Manager privileges required.')
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')

    # Static data for courses page
    context = {
        'user_profile': user_profile,
        'stats': {
            'total_courses': 56,
            'total_courses_trend': '+12%',
            'archive_courses': 14,
            'archive_courses_trend': '0%',
            'draft_pending': 33,
            'draft_pending_trend': '-5%',
            'enrollments': 22,
            'enrollments_trend': '+8%',
        },
        'active_courses_count': 42,
        'course_hours': 320,
    }

    return render(request, 'manager/courses.html', context)

@login_required
def select_role(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        user_id = request.session.get('user_id')
        
        if user_id and role:
            user = User.objects.get(id=user_id)
            
            # Create user profile with social data if available
            UserProfile.objects.create(
                user=user,
                role=role,
                email=request.session.get('social_email', user.email),
                first_name=request.session.get('social_first_name', user.first_name),
                last_name=request.session.get('social_last_name', user.last_name)
            )
            
            # Clean up session
            for key in ['user_id', 'social_email', 'social_first_name', 'social_last_name']:
                request.session.pop(key, None)
            
            messages.success(request, 'Profile created successfully!')
            
            # Redirect based on role
            if role == 'manager':
                return redirect('manager_dashboard')
            elif role == 'employee':
                return redirect('employee_dashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, 'Invalid role selection.')
            
    return render(request, 'select_role.html')

@login_required
def employee_dashboard(request):
    # Check if the user is an employee
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'employee':
            messages.error(request, "Access denied. Employee privileges required.")
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect('home')

    context = {
        'user_profile': user_profile,
    }
    return render(request, 'employee/dashboard.html', context)    