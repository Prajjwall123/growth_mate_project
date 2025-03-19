from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Retail Manager'),
        ('employee', 'Retail Employee'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')

    profile_pic = models.ImageField(upload_to='static/profile_images/', blank=True, default='static/assets/images/defaultuser.png')    
    cover_pic = models.ImageField(upload_to='static/cover_images/', blank=True, default='static/assets/images/default_cover.png')    
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    professional_headline = models.CharField(max_length=255, blank=True, null=True) 
    bio = models.TextField(blank=True, null=True)

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.role}"
