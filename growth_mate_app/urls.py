from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

# URL patterns for the growth_mate_app
urlpatterns = [
    # Home and Authentication Routes
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('select-role/', views.select_role, name='select_role'),

    # Course Management Routes
    path('courses/', views.courses_list, name='courses_list'),
    path('courses/new/', views.course_form, name='create_course'),
    path('courses/<int:course_id>/edit/', views.course_form, name='edit_course'),
    path('courses/<int:course_id>/view/', views.view_course, name='view_course'),
    
    # Lesson Management Routes
    path('sections/<int:section_id>/lessons/new/', views.lesson_builder, name='create_lesson'),
    path('sections/<int:section_id>/lessons/<int:lesson_id>/edit/', views.lesson_builder, name='edit_lesson'),
    path('sections/<int:section_id>/lessons/save/', views.save_lesson, name='save_lesson'),

    # Profile Settings Route
    path('profile/settings/', views.profile_settings, name='profile_settings'),

    # Employee Routes
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('employee/courses/', views.my_courses, name='my_courses'),
    path('employee/courses/<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),

    # Manager Routes
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/users/', views.users_view, name='manager_users'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)