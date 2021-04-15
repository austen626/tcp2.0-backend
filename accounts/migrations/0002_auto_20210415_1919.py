# Generated by Django 3.0.4 on 2021-04-15 13:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='city',
            field=models.CharField(max_length=101, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='main_email',
            field=models.CharField(max_length=101, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='state',
            field=models.CharField(max_length=101, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='street',
            field=models.CharField(max_length=101, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='zip',
            field=models.CharField(max_length=101, null=True),
        ),
    ]
