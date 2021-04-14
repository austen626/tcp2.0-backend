from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from .managers import UserManager


# Create your models here.
class Company(models.Model):
    name = models.CharField(max_length=200)
    contact_type = models.CharField(max_length=200, null=True, blank=True)
    contact_code = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Invites(models.Model):
    email = models.CharField(max_length=200)
    user_role = models.CharField(max_length=51, null=True, blank=True)
    invite_token = models.CharField(max_length=1000, null=True, blank=True)
    token_status = models.BooleanField(default=False)  # True for Active and False for Non-Active
    generated_by = models.CharField(max_length=200, null=True)  # User email Who generated this Invite
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dealer_company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL)


class User(AbstractBaseUser, PermissionsMixin):
    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=18, null=True, blank=True)
    authy_id = models.CharField(max_length=12, null=True, blank=True)
    active = models.BooleanField(default=False)  # a admin user; non super-user
    admin = models.BooleanField(default=False)  # Admin Superuser
    dealer = models.BooleanField(default=False)  # Dealer user
    sales = models.BooleanField(default=True)  # Salesperson user
    staff = models.BooleanField(default=False)
    avatar = models.CharField(max_length=1001, null=True, blank=True)
    pass_token = models.CharField(max_length=1000, null=True, blank=True)
    dealer_company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL)
    account_status = models.BooleanField(default=True)  # True for Active Accounts and False for deleted
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    first_name = models.CharField(max_length=101, null=True)
    last_name = models.CharField(max_length=101, null=True)
    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        """Is the user a admin member?"""
        return self.admin

    @property
    def is_active(self):
        """Is the user active?"""
        return self.active

    @property
    def is_dealer(self):
        """Is the user is dealer """
        return self.dealer

    @property
    def is_sales(self):
        """Is the user salesperson?"""
        return self.sales

    @property
    def is_staff(self):
        "Is the user a admin member?"
        return self.staff
