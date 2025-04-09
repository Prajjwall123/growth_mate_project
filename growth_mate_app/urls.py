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

    # Manager Dashboard and Management Routes
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/users/', views.users_view, name='manager_users'),
    path('manager/courses/', views.manager_courses, name='manager_courses'),
    path('manager/courses/add/', views.course_form, name='add_course'),
    path('manager/courses/<int:course_id>/edit/', views.course_form, name='edit_course'),
    path('manager/courses/<int:course_id>/delete/', views.delete_course, name='delete_course'),
    path('manager/courses/<int:course_id>/', views.view_course, name='view_course'),
    path('manager/courses/<int:course_id>/lessons/', views.manage_lessons, name='manage_lessons'),
    path('manager/courses/form/<int:course_id>/', views.course_form, name='course_form'),
    path('manager/courses/form/', views.course_form, name='course_form'),

    # Profile Settings Route
    path('profile/settings/', views.profile_settings, name='profile_settings'),

    # Employee Dashboard Route
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('my-courses/', views.my_courses, name='my_courses'),
    path('available-courses/', views.available_courses, name='available_courses'),
    path('enroll-course/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('courses/<int:course_id>/details/', views.course_details, name='course_details'),
    path('courses/<int:course_id>/continue/', views.continue_course, name='continue_course'),
    path('lessons/<int:lesson_id>/', views.view_lesson, name='view_lesson'),
    path('users/', views.users_view, name='users'),
    path('users/export/', views.export_users, name='export_users'),
    path('users/toggle-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),

    # Admin Dashboard Route
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)