# Generated by Django 3.0.4 on 2021-04-15 14:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20210415_1919'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='main_email',
            new_name='contact_email',
        ),
    ]
