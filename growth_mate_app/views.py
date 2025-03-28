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
from .models import Course, UserProfile, Lesson, Enrollment, CourseSection
from .tokens import generate_token  
from growth_mate_project import settings 
from django.http import JsonResponse
from django.core.mail import send_mail
import random
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, F, Q
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from social_django.utils import load_strategy, load_backend
from social_core.backends.oauth import BaseOAuth2PKCE
from social_core.exceptions import MissingBackend
import json
from django.urls import reverse


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

    # Get total users (employees)
    total_users = UserProfile.objects.filter(role='employee').count()
    
    # Get courses created by this manager
    manager_courses = Course.objects.filter(uploaded_by=request.user)
    total_courses = manager_courses.count()
    active_courses = manager_courses.filter(is_active=True).count()
    
    # Get top students based on course progress
    top_students = []
    enrollments = Enrollment.objects.filter(course__in=manager_courses).values('user').annotate(
        avg_progress=Avg('progress')
    ).order_by('-avg_progress')[:4]
    
    for enrollment in enrollments:
        user = User.objects.get(id=enrollment['user'])
        top_students.append({
            'name': f"{user.first_name} {user.last_name}",
            'progress': round(enrollment['avg_progress'])
        })
    
    # Get course completion data
    course_completion = []
    for course in manager_courses:
        enrollments = Enrollment.objects.filter(course=course)
        if enrollments.exists():
            avg_progress = enrollments.aggregate(avg_progress=Avg('progress'))['avg_progress']
            course_completion.append({
                'title': course.title,
                'progress': round(avg_progress),
                'total': 100
            })

    context = {
        'user_profile': user_profile,
        'total_users': total_users,
        'total_courses': total_courses,
        'active_courses': active_courses,
        'top_students': top_students,
        'course_completion': course_completion
    }
    
    return render(request, 'manager/dashboard.html', context)

@login_required
def my_courses(request):
    # Check if user is an employee
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'employee':
            messages.error(request, "Access denied. Employee privileges required.")
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect('home')

    # Get enrolled courses
    enrolled_courses = Course.objects.filter(enrollment__user=request.user)
    
    # Get available courses (courses not enrolled in)
    available_courses = Course.objects.filter(is_active=True).exclude(enrollment__user=request.user)
    
    # Get course progress for enrolled courses
    course_progress = []
    for course in enrolled_courses:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
        course_progress.append({
            'course': course,
            'progress': enrollment.progress,
            'enrollment': enrollment
        })
    
    context = {
        'user_profile': user_profile,
        'enrolled_courses': course_progress,
        'available_courses': available_courses
    }
    
    return render(request, 'employee/my_courses.html', context)

@login_required
@require_POST
def add_course(request):
    # Check if the user is a manager
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'manager':
            return JsonResponse({'success': False, 'message': 'Access denied. Manager privileges required.'})
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User profile not found.'})

    try:
        # Get form data
        title = request.POST.get('title')
        duration = request.POST.get('duration')
        due_date = request.POST.get('due_date')
        description = request.POST.get('description')
        image = request.FILES.get('image')

        # Validate required fields
        if not all([title, duration, due_date, description]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('create_course')

        # Create course
        course = Course.objects.create(
            title=title,
            duration=duration,
            due_date=due_date,
            description=description,
            uploaded_by=request.user
        )

        # Handle image upload if provided
        if image:
            course.image = image
            course.save()

        return JsonResponse({
            'success': True,
            'message': 'Course created successfully.',
            'course_id': course.id,
            'course_title': course.title
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating course: {str(e)}'
        })

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
            course.description = request.POST['description']
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
    
    # Check if user has permission to view this course
    if not course.is_visible_to(request.user):
        messages.error(request, "Access denied. You don't have permission to view this course.")
        return redirect('home')

    sections = course.sections.all().prefetch_related('lessons')
    
    return render(request, 'view_course.html', {
        'course': course,
        'sections': sections,
        'can_edit': request.user.userprofile.role == 'admin' or course.uploaded_by == request.user
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
            messages.error(request, "Access denied. Manager privileges required.")
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect('home')

    # Get search query
    search_query = request.GET.get('search', '')
    
    # Get courses created by this manager
    courses = Course.objects.filter(uploaded_by=request.user)
    
    # Apply search filter if query exists
    if search_query:
        courses = courses.filter(title__icontains=search_query)
    
    # Get course statistics
    total_courses = courses.count()
    active_courses = courses.filter(is_active=True).count()
    
    # Get enrollment statistics for each course
    course_stats = []
    for course in courses:
        enrollments = Enrollment.objects.filter(course=course)
        total_enrollments = enrollments.count()
        avg_progress = enrollments.aggregate(avg_progress=Avg('progress'))['avg_progress'] or 0
        
        course_stats.append({
            'course': course,
            'total_enrollments': total_enrollments,
            'avg_progress': round(avg_progress)
        })
    
    # Paginate results
    paginator = Paginator(course_stats, 10)  # Show 10 courses per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'user_profile': user_profile,
        'courses': page_obj,
        'total_courses': total_courses,
        'active_courses': active_courses,
        'search_query': search_query
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

    # Get employee's enrollments
    enrollments = Enrollment.objects.filter(user=request.user)
    
    # Calculate overall progress
    overall_progress = 0
    if enrollments.exists():
        overall_progress = round(enrollments.aggregate(avg_progress=Avg('progress'))['avg_progress'] or 0)
    
    # Get total courses and active courses
    total_courses = enrollments.count()
    active_courses = enrollments.filter(course__is_active=True).count()
    
    # Calculate learning time (sum of course durations)
    learning_time = sum(int(course.duration.split()[0]) for course in Course.objects.filter(
        enrollment__user=request.user
    ).distinct())
    
    # Get course progress data
    course_progress = []
    for enrollment in enrollments:
        course_progress.append({
            'title': enrollment.course.title,
            'progress': enrollment.progress
        })

    context = {
        'user_profile': user_profile,
        'overall_progress': overall_progress,
        'total_courses': total_courses,
        'active_courses': active_courses,
        'learning_time': learning_time,
        'course_progress': course_progress
    }
    
    return render(request, 'employee/dashboard.html', context)

@login_required
def course_details(request, course_id=None):
    # For now, using static data
    course_data = {
        'title': 'Customer Service',
        'duration': '3hrs',
        'due_date': 'Jan 30, 2025',
        'progress': 70,
        'image': 'https://picsum.photos/1200/400?random=1',
        'about': 'This course provides an in-depth overview of customer service skills and best practices. You\'ll learn how to effectively communicate with customers, handle difficult situations, and provide exceptional service that builds long-term relationships. The course combines theoretical knowledge with practical examples and real-world scenarios.',
        'lessons': [
            {
                'number': 1,
                'title': 'Introduction to Customer Service',
                'duration': '45 mins'
            },
            {
                'number': 2,
                'title': 'Communication Skills',
                'duration': '60 mins'
            },
            {
                'number': 3,
                'title': 'Handling Customer Complaints',
                'duration': '75 mins'
            }
        ],
        'stats': {
            'total_lessons': 3,
            'completed_lessons': 2,
            'time_remaining': '75 mins',
            'last_accessed': '2 days ago'
        }
    }
    
    return render(request, 'employee/course_details.html', {'course': course_data})

@login_required
@require_POST
def enroll_course(request, course_id):
    # Check if user is an employee
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.role != 'employee':
            return JsonResponse({'success': False, 'message': 'Access denied. Employee privileges required.'})
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User profile not found.'})

    try:
        course = Course.objects.get(id=course_id)
        
        # Check if already enrolled
        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return JsonResponse({
                'success': False,
                'message': 'You are already enrolled in this course.'
            })
        
        # Create enrollment
        Enrollment.objects.create(
            user=request.user,
            course=course,
            progress=0
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Successfully enrolled in the course.',
            'course_title': course.title
        })
        
    except Course.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Course not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error enrolling in course: {str(e)}'
        })

@login_required
def course_form(request, course_id=None):
    # Check if user has permission to manage courses
    if not request.user.userprofile.role in ['admin', 'manager']:
        messages.error(request, "Access denied. You don't have permission to manage courses.")
        return redirect('home')

    course = None
    if course_id:
        course = get_object_or_404(Course, id=course_id)
        # Check if user has permission to edit this course
        if not (request.user.userprofile.role == 'admin' or course.uploaded_by == request.user):
            messages.error(request, "Access denied. You don't have permission to edit this course.")
            return redirect('home')

    if request.method == 'POST':
        data = request.POST
        files = request.FILES

        try:
            if course:
                # Update existing course
                course.title = data.get('title')
                course.difficulty_level = data.get('difficulty_level')
                course.category = data.get('category')
                course.tags = data.get('tags')
                course.description = data.get('description')
                course.course_language = data.get('course_language')
                course.duration = data.get('duration')
                course.due_date = data.get('due_date')
                course.is_active = data.get('is_active') == 'on'
                course.enable_comments = data.get('enable_comments') == 'on'
                course.student_limit = data.get('student_limit') or None
                
                if 'image' in files:
                    course.image = files['image']
                
                course.save()
                messages.success(request, 'Course updated successfully!')
            else:
                # Create new course
                course = Course.objects.create(
                    title=data.get('title'),
                    difficulty_level=data.get('difficulty_level'),
                    category=data.get('category'),
                    tags=data.get('tags'),
                    description=data.get('description'),
                    course_language=data.get('course_language'),
                    duration=data.get('duration'),
                    due_date=data.get('due_date'),
                    is_active=data.get('is_active') == 'on',
                    enable_comments=data.get('enable_comments') == 'on',
                    student_limit=data.get('student_limit') or None,
                    uploaded_by=request.user,
                    image=files.get('image')
                )
                messages.success(request, 'Course created successfully!')

            return redirect('view_course', course_id=course.id)

        except Exception as e:
            messages.error(request, f'Error saving course: {str(e)}')
            return render(request, 'course_form.html', {'course': course})

    return render(request, 'course_form.html', {'course': course})

@login_required
def lesson_builder(request, section_id, lesson_id=None):
    section = get_object_or_404(CourseSection, id=section_id)
    course = section.course

    # Check if user has permission to manage this course's lessons
    if not (request.user.userprofile.role == 'admin' or course.uploaded_by == request.user):
        messages.error(request, "Access denied. You don't have permission to manage lessons for this course.")
        return redirect('view_course', course_id=course.id)

    lesson = None
    if lesson_id:
        lesson = get_object_or_404(Lesson, id=lesson_id, section=section)

    return render(request, 'lesson_builder.html', {
        'section': section,
        'lesson': lesson,
        'course': course
    })

@login_required
@require_POST
def save_lesson(request, section_id):
    section = get_object_or_404(CourseSection, id=section_id)
    course = section.course

    # Check permissions
    if not (request.user.userprofile.role == 'admin' or course.uploaded_by == request.user):
        return JsonResponse({
            'success': False,
            'message': "Access denied. You don't have permission to manage lessons for this course."
        })

    try:
        # Get lesson data
        data = request.POST
        files = request.FILES
        blocks_data = json.loads(data.get('blocks', '[]'))

        # Create or update lesson
        lesson_id = data.get('lesson_id')
        if lesson_id:
            lesson = get_object_or_404(Lesson, id=lesson_id, section=section)
            lesson.title = data.get('title')
            lesson.duration = data.get('duration')
            lesson.save()
        else:
            lesson = Lesson.objects.create(
                section=section,
                title=data.get('title'),
                duration=data.get('duration')
            )

        # Process content blocks
        for index, block_data in enumerate(blocks_data):
            content_type = block_data['type']
            content = block_data.get('content', '')
            file_key = f'block_{index}_file'
            
            # Create content block
            block = lesson.content_blocks.create(
                content_type=content_type,
                content=content,
                order=index
            )
            
            # Handle file uploads
            if file_key in files:
                block.file = files[file_key]
                block.save()

        return JsonResponse({
            'success': True,
            'message': 'Lesson saved successfully!',
            'redirect_url': request.build_absolute_uri(reverse('view_course', args=[course.id]))
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving lesson: {str(e)}'
        })

@login_required
def courses_list(request):
    user_profile = request.user.userprofile
    search_query = request.GET.get('search', '')
    
    # Get courses based on user role and visibility
    if user_profile.role == 'admin':
        courses = Course.objects.all()
    elif user_profile.role == 'manager':
        courses = Course.objects.filter(
            Q(uploaded_by=request.user) |  # Own courses
            Q(uploaded_by__userprofile__role='admin')  # Admin courses
        )
    else:  # Employee
        courses = Course.objects.filter(
            Q(is_active=True) &
            (Q(uploaded_by__userprofile__role='admin') |  # Admin courses
             Q(uploaded_by__userprofile__role='manager'))  # Manager courses
        )
    
    # Apply search filter
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    # Order courses
    courses = courses.order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(courses, 12)  # Show 12 courses per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'courses_list.html', {
        'courses': page_obj,
        'search_query': search_query,
        'user_profile': user_profile
    })    