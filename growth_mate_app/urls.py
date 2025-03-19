from django.urls import path
from .views import signup, login_view, logout_view, home, activate

urlpatterns = [
    path('', home, name='home'),
    path('signup', signup, name='signup'),
    path('login', login_view, name='login'),
    path('logout', logout_view, name='logout'),
    path('activate/<uidb64>/<token>', activate, name='activate'),
]
