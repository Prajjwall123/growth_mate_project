# Generated by Django 4.2.10 on 2025-03-23 19:06

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('growth_mate_app', '0006_alter_userprofile_profile_pic'),
    ]

    operations = [
        migrations.CreateModel(
            name='Lesson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField()),
                ('duration', models.IntegerField(help_text='Duration in minutes')),
                ('order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='growth_mate_app.course')),
            ],
            options={
                'ordering': ['order', 'created_at'],
            },
        ),
    ]
