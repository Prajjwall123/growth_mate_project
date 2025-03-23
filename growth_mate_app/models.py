from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Retail Manager'),
        ('employee', 'Retail Employee'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')

    profile_pic = models.ImageField(upload_to='static/profile_pics/', blank=True, default='static/assets/images/default_profile.png')
    cover_image = models.ImageField(upload_to='static/cover_images/', blank=True, default='static/assets/images/default_cover.png')
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    professional_headline = models.CharField(max_length=255, blank=True, null=True) 
    bio = models.TextField(blank=True, null=True)

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, default='')
    is_phone_verified = models.BooleanField(default=False)
    headline = models.CharField(max_length=100, blank=True)

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.role}"


class Course(models.Model):
    image = models.ImageField(upload_to='static/course_images/', blank=True, default='static/assets/images/default_course.png')  
    title = models.CharField(max_length=255)
    duration = models.CharField(max_length=50) 
    due_date = models.DateField()
    about_this_course = models.TextField()
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def total_lessons(self):
        return self.lesson_set.count()

    @property
    def total_duration(self):
        return sum(lesson.duration for lesson in self.lesson_set.all())


class CourseContent(models.Model):
    course = models.ForeignKey(Course, related_name="contents", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    images = models.ImageField(upload_to='static/course_content/images/', blank=True, null=True)
    videos = models.FileField(upload_to='static/course_content/videos/', blank=True, null=True) 

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Section(models.Model):
    course_content = models.ForeignKey(CourseContent, related_name="sections", on_delete=models.CASCADE)
    heading = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True) 
    images = models.ImageField(upload_to='static/course_media/images/', blank=True, null=True) 
    videos = models.FileField(upload_to='static/course_media/videos/', blank=True, null=True) 

    def __str__(self):
        return self.heading


class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    progress = models.IntegerField(default=0)  # Store progress as percentage

    class Meta:
        unique_together = ['user', 'course']

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    duration = models.IntegerField(help_text='Duration in minutes')
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.course.title} - {self.title}"