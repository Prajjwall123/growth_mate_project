from django.contrib import admin
from .models import UserProfile, Course, CourseContent, Section
from django.db import models


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['get_user', 'role', 'get_first_name', 'get_last_name', 'get_email', 'get_phone_number']

    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = 'User'

    def get_first_name(self, obj):
        return obj.first_name
    get_first_name.short_description = 'First Name'

    def get_last_name(self, obj):
        return obj.last_name
    get_last_name.short_description = 'Last Name'

    def get_email(self, obj):
        return obj.email
    get_email.short_description = 'Email'

    def get_phone_number(self, obj):
        return obj.phone_number
    get_phone_number.short_description = 'Phone Number'


class SectionInline(admin.StackedInline):
    model = Section
    extra = 1 
    fields = ('heading', 'description', 'images', 'videos')


class CourseContentInline(admin.StackedInline):
    model = CourseContent
    extra = 1 
    fields = ('title', 'description', 'images', 'videos')
    inlines = [SectionInline] 


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration', 'due_date', 'uploaded_by')
    search_fields = ('title', 'uploaded_by__username')
    list_filter = ('due_date',)
    ordering = ('-due_date',)
    inlines = [CourseContentInline]  


@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'course')
    search_fields = ('title', 'course__title')


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('heading', 'course_content')
    search_fields = ('heading', 'course_content__title')