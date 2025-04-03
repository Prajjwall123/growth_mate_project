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
from .models import Course, UserProfile, Lesson, DashboardStats, StudentProgress, Enrollment, CourseCategory, CourseTag, ContentBlock
from .tokens import generate_token  
from growth_mate_project import settings 
from django.http import JsonResponse
from django.core.mail import send_mail
import random
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from social_django.utils import load_strategy, load_backend
from social_core.backends.oauth import BaseOAuth2PKCE
from social_core.exceptions import MissingBackend
from django.db.models import Q


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

        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Store user data and OTP in session
        request.session['temp_user_data'] = {
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'role': role
        }
        request.session['otp'] = otp
        request.session.set_expiry(300)  # 5 minutes expiry

        # Send OTP email
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
        stored_otp = request.session.get('otp')

        if not email or not stored_otp:
            messages.error(request, "Session expired. Please register again.")
            return redirect("signup")

        if stored_otp == entered_otp:
            user_data = request.session.get('temp_user_data')

            # Create user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=user_data['password'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name']
            )

            # Create user profile
            UserProfile.objects.create(
                user=user,
                role=user_data['role']
            )

            # Clear session data
            request.session.pop('temp_user_data', None)
            request.session.pop('otp', None)

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

    # Get today's date and last month's date
    today = timezone.now().date()
    last_month = today - timezone.timedelta(days=30)

    # Get or create today's statistics
    today_stats, created = DashboardStats.objects.get_or_create(date=today)
    last_month_stats = DashboardStats.objects.filter(date=last_month).first()

    # Calculate total users (employees only)
    total_users = User.objects.filter(userprofile__role='employee').count()
    active_users = User.objects.filter(userprofile__role='employee', is_active=True).count()
    inactive_users = total_users - active_users

    # Calculate course statistics
    total_courses = Course.objects.filter(instructor=request.user).count()
    active_courses = Course.objects.filter(instructor=request.user, is_active=True).count()
    
    # Calculate course completion rate
    enrollments = Enrollment.objects.filter(course__instructor=request.user)
    total_enrollments = enrollments.count()
    completed_enrollments = enrollments.filter(completed=True).count()
    course_completion = round((completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0, 2)

    # Calculate growth rates
    if last_month_stats:
        user_growth = round(((total_users - last_month_stats.total_users) / last_month_stats.total_users * 100) if last_month_stats.total_users > 0 else 0, 2)
        course_growth = round(((total_courses - last_month_stats.total_courses) / last_month_stats.total_courses * 100) if last_month_stats.total_courses > 0 else 0, 2)
        completion_growth = round((course_completion - last_month_stats.course_completion_rate), 2)
    else:
        user_growth = 0
        course_growth = 0
        completion_growth = 0

    # Update today's statistics
    today_stats.total_users = total_users
    today_stats.total_courses = total_courses
    today_stats.active_courses = active_courses
    today_stats.course_completion_rate = course_completion
    today_stats.user_growth_rate = user_growth
    today_stats.course_growth_rate = course_growth
    today_stats.completion_growth_rate = completion_growth
    today_stats.save()

    # Get top students based on progress
    top_students = StudentProgress.objects.filter(
        course__instructor=request.user
    ).select_related('user').order_by('-progress_percentage')[:5]

    # Get course completion data
    courses = Course.objects.filter(instructor=request.user)
    course_completion_data = []
    for course in courses:
        course_completion_data.append({
            'title': course.title,
            'completion_rate': course.completion_rate
        })

    context = {
        'user_profile': user_profile,
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'total_courses': total_courses,
            'active_courses': active_courses,
            'course_completion': course_completion,
            'user_growth': user_growth,
            'course_growth': course_growth,
            'completion_growth': completion_growth
        },
        'top_students': top_students,
        'course_completion_data': course_completion_data
    }
    
    return render(request, 'manager/dashboard.html', context)

@login_required
def my_courses(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    if user_profile.role == 'manager':
        courses = Course.objects.filter(instructor=request.user).order_by('-created_at')
        template = 'manager/my_courses.html'
    else:  # employee
        # Get courses through the enrollments related name
        enrolled_courses = Course.objects.filter(
            enrollments__user=request.user
        ).order_by('-created_at')
        courses = enrolled_courses
        template = 'employee/my_courses.html'
    
    # Add additional course data
    for course in courses:
        course.enrolled_students_count = course.enrollments.count()
        course.active_enrollments_count = course.enrollments.filter(completed=False).count()
    
    return render(request, template, {
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
        if 'profile_picture' in request.FILES:
            print("Profile picture uploaded:", request.FILES['profile_picture'])
            user_profile.profile_picture = request.FILES['profile_picture']
            user_profile.save()
            messages.success(request, 'Profile picture updated successfully.')
            return redirect('profile_settings')
            
        if 'cover_image' in request.FILES:
            print("Cover image uploaded:", request.FILES['cover_image'])
            user_profile.cover_image = request.FILES['cover_image']
            user_profile.save()
            messages.success(request, 'Cover image updated successfully.')
            return redirect('profile_settings')

        # Update user fields
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.save()

        # Update profile fields
        if user_profile.role == 'manager':
            user_profile.professional_headline = request.POST.get('professional_headline', user_profile.professional_headline)
        user_profile.bio = request.POST.get('bio', user_profile.bio)
        user_profile.phone = request.POST.get('phone', user_profile.phone)
        user_profile.gender = request.POST.get('gender', user_profile.gender)
        user_profile.country = request.POST.get('country', user_profile.country)
        user_profile.city = request.POST.get('city', user_profile.city)
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

    # Get search query and filters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')
    page = request.GET.get('page', 1)

    # Base queryset for employees
    employees = User.objects.filter(userprofile__role='employee')

    # Apply search filter
    if search_query:
        employees = employees.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Apply status filter
    if status_filter == 'active':
        employees = employees.filter(is_active=True)
    elif status_filter == 'inactive':
        employees = employees.filter(is_active=False)

    # Calculate statistics
    total_users = User.objects.filter(userprofile__role='employee').count()
    active_users = User.objects.filter(userprofile__role='employee', is_active=True).count()
    inactive_users = total_users - active_users

    # Calculate average course completion rate
    enrollments = Enrollment.objects.filter(user__userprofile__role='employee')
    total_enrollments = enrollments.count()
    completed_enrollments = enrollments.filter(completed=True).count()
    course_completion = round((completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0, 2)

    # Paginate the results
    paginator = Paginator(employees, 10)  # Show 10 users per page
    try:
        employees = paginator.page(page)
    except PageNotAnInteger:
        employees = paginator.page(1)
    except EmptyPage:
        employees = paginator.page(paginator.num_pages)

    # Get additional user data
    for employee in employees:
        # Get enrolled courses count
        employee.enrolled_courses_count = Enrollment.objects.filter(user=employee).count()
        # Get completed courses count
        employee.completed_courses_count = Enrollment.objects.filter(user=employee, completed=True).count()
        # Get last login
        employee.last_login = employee.last_login.strftime('%Y-%m-%d %H:%M') if employee.last_login else 'Never'

    context = {
        'user_profile': user_profile,
        'employees': employees,
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'course_completion': course_completion
        },
        'search_query': search_query,
        'status_filter': status_filter,
        'page_obj': employees,
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

@login_required
def available_courses(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Get all active courses that the user is not enrolled in
    enrolled_course_ids = Course.objects.filter(
        enrollments__user=request.user
    ).values_list('id', flat=True)
    
    available_courses = Course.objects.filter(
        is_active=True
    ).exclude(
        id__in=enrolled_course_ids
    ).order_by('-created_at')
    
    return render(request, 'employee/available_courses.html', {
        'courses': available_courses,
        'user_profile': user_profile
    })

@login_required
def manager_courses(request):
    if not request.user.userprofile.role == 'manager':
        messages.error(request, 'Access denied. Only managers can access this page.')
        return redirect('home')
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', 'all')
    status_filter = request.GET.get('status', 'all')
    
    # Get courses for the logged-in instructor
    courses = Course.objects.filter(instructor=request.user)
    
    # Apply filters
    if search_query:
        courses = courses.filter(title__icontains=search_query)
    if category_filter != 'all':
        courses = courses.filter(category_id=category_filter)
    if status_filter != 'all':
        courses = courses.filter(is_active=(status_filter == 'active'))
    
    # Calculate statistics
    stats = {
        'total_courses': courses.count(),
        'active_courses': courses.filter(is_active=True).count(),
        'total_enrollments': Enrollment.objects.filter(course__in=courses).count(),
        'completion_rate': 0
    }
    
    # Calculate completion rate
    total_enrollments = Enrollment.objects.filter(course__in=courses).count()
    if total_enrollments > 0:
        completed_enrollments = Enrollment.objects.filter(
            course__in=courses,
            completed=True
        ).count()
        stats['completion_rate'] = round((completed_enrollments / total_enrollments) * 100, 1)
    
    # Add additional course data
    for course in courses:
        course.enrolled_students_count = course.enrollments.count()
        course.active_enrollments_count = course.enrollments.filter(completed=False).count()
    
    # Pagination
    paginator = Paginator(courses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'user_profile': request.user.userprofile,
        'courses': page_obj,
        'stats': stats,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
    }
    return render(request, 'manager/courses.html', context)

@login_required
def course_form(request, course_id=None):
    # Check if user is a manager
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'manager':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')

    course = None
    if course_id:
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            messages.error(request, 'Course not found.')
            return redirect('manager_courses')

    if request.method == 'POST':
        # Handle course data
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        level = request.POST.get('level')
        duration = request.POST.get('duration')
        prerequisites = request.POST.get('prerequisites')
        objectives = request.POST.get('objectives')
        target_audience = request.POST.get('target_audience')
        max_students = request.POST.get('max_students')
        is_active = request.POST.get('is_active') == 'on'
        is_featured = request.POST.get('is_featured') == 'on'
        certificate_available = request.POST.get('certificate_available') == 'on'

        # Handle thumbnail
        thumbnail = request.FILES.get('thumbnail')
        if thumbnail and course and course.thumbnail:
            # Delete old thumbnail if it exists
            course.thumbnail.delete()

        # Create or update course
        if not course:
            course = Course.objects.create(
                title=title,
                description=description,
                category_id=category_id,
                level=level,
                duration=duration,
                prerequisites=prerequisites,
                objectives=objectives,
                target_audience=target_audience,
                max_students=max_students,
                is_active=is_active,
                is_featured=is_featured,
                certificate_available=certificate_available,
                thumbnail=thumbnail,
                instructor=request.user
            )
        else:
            course.title = title
            course.description = description
            course.category_id = category_id
            course.level = level
            course.duration = duration
            course.prerequisites = prerequisites
            course.objectives = objectives
            course.target_audience = target_audience
            course.max_students = max_students
            course.is_active = is_active
            course.is_featured = is_featured
            course.certificate_available = certificate_available
            if thumbnail:
                course.thumbnail = thumbnail
            course.save()

        # Handle lessons
        lesson_titles = request.POST.getlist('lesson_title[]')
        lesson_durations = request.POST.getlist('lesson_duration[]')
        
        # Delete existing lessons if updating
        if course_id:
            course.lessons.all().delete()

        # Create new lessons
        for i in range(len(lesson_titles)):
            if lesson_titles[i] and lesson_durations[i]:
                lesson = Lesson.objects.create(
                    course=course,
                    title=lesson_titles[i],
                    duration=lesson_durations[i],
                    order=i
                )

                # Handle content blocks for this lesson
                content_blocks = request.POST.getlist(f'lesson_{i}_content_blocks[]')
                content_types = request.POST.getlist(f'lesson_{i}_content_types[]')
                content_files = request.FILES.getlist(f'lesson_{i}_content_files[]')

                for j in range(len(content_blocks)):
                    if content_blocks[j]:
                        content_type = content_types[j]
                        content = content_blocks[j]
                        file = content_files[j] if j < len(content_files) else None

                        ContentBlock.objects.create(
                            lesson=lesson,
                            content_type=content_type,
                            content=content,
                            file=file,
                            order=j
                        )

        messages.success(request, f'Course {"updated" if course_id else "created"} successfully.')
        return redirect('manager_courses')

    # Get categories for the form
    categories = CourseCategory.objects.all()

    context = {
        'course': course,
        'categories': categories,
    }
    return render(request, 'manager/course_form.html', context)

@login_required
def delete_course(request, course_id):
    # Check if the user is a manager
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'manager':
            messages.error(request, "Access denied. Manager privileges required.")
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect('home')

    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Course deleted successfully.')
        return redirect('manager_courses')
    
    context = {
        'user_profile': user_profile,
        'course': course,
    }
    
    return render(request, 'manager/delete_course.html', context)

@login_required
def enroll_course(request, course_id):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'employee':
        messages.error(request, 'Only employees can enroll in courses.')
        return redirect('home')
    
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Check if user is already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.warning(request, 'You are already enrolled in this course.')
        return redirect('my_courses')
    
    # Check if course has reached maximum students
    if course.max_students and course.enrollments.count() >= course.max_students:
        messages.error(request, 'This course has reached its maximum number of students.')
        return redirect('available_courses')
    
    try:
        # Create enrollment
        Enrollment.objects.create(
            user=request.user,
            course=course,
            enrolled_at=timezone.now()
        )
        messages.success(request, f'Successfully enrolled in {course.title}!')
        return redirect('my_courses')
    except Exception as e:
        messages.error(request, f'Error enrolling in course: {str(e)}')
        return redirect('available_courses')

@login_required
def manage_lessons(request, course_id):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'manager':
            messages.error(request, 'You do not have permission to manage lessons.')
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')

    course = get_object_or_404(Course, id=course_id, instructor=request.user)

    if request.method == 'POST':
        try:
            print("\n=== POST Request Data ===")
            print("POST data:", dict(request.POST))
            print("FILES data:", dict(request.FILES))

            # Get lesson data
            lesson_titles = request.POST.getlist('lesson_title[]')
            lesson_durations = request.POST.getlist('lesson_duration[]')
            lesson_ids = request.POST.getlist('lesson_ids[]') if 'lesson_ids[]' in request.POST else []
            lesson_deleted = request.POST.getlist('lesson_deleted[]') if 'lesson_deleted[]' in request.POST else []

            print("\n=== Lesson Data ===")
            print(f"Titles: {lesson_titles}")
            print(f"Durations: {lesson_durations}")
            print(f"IDs: {lesson_ids}")
            print(f"Deleted: {lesson_deleted}")

            # Handle existing lessons
            if lesson_ids:
                existing_lessons = {str(lesson.id): lesson for lesson in course.lessons.all()}
                for index, (lesson_id, is_deleted) in enumerate(zip(lesson_ids, lesson_deleted)):
                    if lesson_id and lesson_id in existing_lessons:
                        lesson = existing_lessons[lesson_id]
                        if is_deleted == 'true':
                            lesson.delete()
                        else:
                            lesson.title = lesson_titles[index]
                            lesson.duration = lesson_durations[index]
                            lesson.order = index
                            lesson.save()

            # Handle new lessons
            for index, (title, duration) in enumerate(zip(lesson_titles, lesson_durations)):
                # Create new lesson if no valid lesson_id exists at this index
                if index >= len(lesson_ids) or not lesson_ids[index]:
                    lesson = Lesson.objects.create(
                        course=course,
                        title=title,
                        duration=duration,
                        order=index
                    )
                    print(f"\nCreated new lesson: {lesson.id}")

                    # Handle content blocks
                    content_blocks = request.POST.getlist('content_block_text[]')
                    content_types = request.POST.getlist('lesson_undefined_content_block_type[]')
                    content_files = request.FILES.getlist('lesson_undefined_content_block_file[]')

                    print(f"\nContent blocks: {content_blocks}")
                    print(f"Content types: {content_types}")
                    print(f"Files: {content_files}")

                    for i, content_type in enumerate(content_types):
                        content = content_blocks[i] if i < len(content_blocks) else None
                        file = content_files[i] if i < len(content_files) else None
                        if content or file:
                            try:
                                content_block = ContentBlock.objects.create(
                                    lesson=lesson,
                                    content_type=content_type,
                                    content=content,
                                    file=file,
                                    order=i
                                )
                                print(f"Created content block: {content_block.id}")
                            except Exception as e:
                                print(f"Error creating content block: {str(e)}")

            messages.success(request, 'Lessons updated successfully.')
            return redirect('course_form', course_id=course.id)

        except Exception as e:
            print(f"\nError in manage_lessons: {str(e)}")
            messages.error(request, f'Error updating lessons: {str(e)}')
            return redirect('course_form', course_id=course.id)

    else:
        # Handle GET request
        lessons = course.lessons.all().order_by('order')
        context = {
            'course': course,
            'lessons': lessons,
        }
        return render(request, 'manager/manage_lessons.html', context)
