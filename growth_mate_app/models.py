from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Retail Manager'),
        ('employee', 'Retail Employee'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')

    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )
    cover_image = models.ImageField(
        upload_to='cover_images/',
        blank=True,
        null=True
    )
    professional_headline = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)

    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.role}"

class Course(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='static/course_images/', blank=True, default='static/assets/images/default_course.png')
    difficulty_level = models.CharField(max_length=50, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ], default='beginner')
    category = models.CharField(max_length=100, blank=True, null=True, default='General')
    tags = models.CharField(max_length=255, blank=True, help_text='Comma-separated tags')
    description = models.TextField(blank=True, null=True)
    course_language = models.CharField(max_length=50, default='English')
    duration = models.CharField(max_length=50, default='1 hour')
    due_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    enable_comments = models.BooleanField(default=True)
    student_limit = models.IntegerField(null=True, blank=True)
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

    @property
    def is_admin_course(self):
        return self.uploaded_by.userprofile.role == 'admin'

    def is_visible_to(self, user):
        if not user.is_authenticated:
            return False
        uploader_role = self.uploaded_by.userprofile.role
        user_role = user.userprofile.role
        
        if uploader_role == 'admin':
            return True
        elif uploader_role == 'manager':
            return user_role in ['manager', 'employee']
        return False

class CourseSection(models.Model):
    course = models.ForeignKey(Course, related_name='sections', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    CONTENT_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('file', 'File'),
        ('pdf', 'PDF')
    ]

    section = models.ForeignKey(CourseSection, related_name='lessons', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default='text')
    content = models.TextField()
    file = models.FileField(upload_to='static/lesson_files/', null=True, blank=True)
    duration = models.IntegerField(help_text='Duration in minutes', default=0)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.section.course.title} - {self.section.title} - {self.title}" if self.section else self.title

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