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
    path('manager/courses/', views.courses_view, name='manager_courses'),
    path('manager/courses/add/', views.add_course, name='add_course'),
    path('manager/courses/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    path('manager/courses/<int:course_id>/', views.view_course, name='view_course'),
    path('manager/lessons/add/', views.add_lesson, name='add_lesson'),

    # Profile Settings Route
    path('profile/settings/', views.profile_settings, name='profile_settings'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)