from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/users/', views.users_view, name='manager_users'),
    path('manager/courses/', views.courses_view, name='manager_courses'),
    path('manager/courses/add/', views.add_course, name='add_course'),
    path('manager/courses/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    path('manager/courses/<int:course_id>/', views.view_course, name='view_course'),
    path('manager/lessons/add/', views.add_lesson, name='add_lesson'),
    path('manager/profile/settings/', views.profile_settings, name='profile_settings'),
]
