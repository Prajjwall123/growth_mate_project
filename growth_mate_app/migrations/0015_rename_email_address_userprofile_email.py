# Generated by Django 4.2.10 on 2025-03-29 14:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('growth_mate_app', '0014_rename_email_userprofile_email_address'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userprofile',
            old_name='email_address',
            new_name='email',
        ),
    ]
