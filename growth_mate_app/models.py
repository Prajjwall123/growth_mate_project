from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django_cleanup.signals import cleanup_pre_delete
from sorl.thumbnail import ImageField, delete

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Retail Manager'),
        ('employee', 'Retail Employee'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')

    profile_picture = ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )
    cover_image = ImageField(
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

    def save(self, *args, **kwargs):
        # Delete old profile picture if it exists and is being updated
        if self.pk:
            try:
                old_instance = UserProfile.objects.get(pk=self.pk)
                if old_instance.profile_picture and self.profile_picture != old_instance.profile_picture:
                    old_instance.profile_picture.delete(save=False)
                if old_instance.cover_image and self.cover_image != old_instance.cover_image:
                    old_instance.cover_image.delete(save=False)
            except UserProfile.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete files when the profile is deleted
        if self.profile_picture:
            self.profile_picture.delete(save=False)
        if self.cover_image:
            self.cover_image.delete(save=False)
        super().delete(*args, **kwargs)

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

    @property
    def completion_rate(self):
        total_enrollments = self.enrollment_set.count()
        if total_enrollments == 0:
            return 0
        completed_enrollments = self.enrollment_set.filter(completed=True).count()
        return round((completed_enrollments / total_enrollments) * 100, 2)

    @property
    def active_enrollments(self):
        return self.enrollment_set.filter(completed=False).count()

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
    last_accessed = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'course']

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"

    def save(self, *args, **kwargs):
        if self.completed and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

class DashboardStats(models.Model):
    date = models.DateField(unique=True)
    total_users = models.IntegerField(default=0)
    total_courses = models.IntegerField(default=0)
    active_courses = models.IntegerField(default=0)
    course_completion_rate = models.FloatField(default=0)
    user_growth_rate = models.FloatField(default=0)
    course_growth_rate = models.FloatField(default=0)
    completion_growth_rate = models.FloatField(default=0)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Stats for {self.date}"

class StudentProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    progress_percentage = models.FloatField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'course']
        ordering = ['-progress_percentage']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.course.title} - {self.progress_percentage}%"

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