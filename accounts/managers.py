from django.contrib.auth.models import BaseUserManager

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, authy_id, password,
                     **extra_fields):
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, authy_id=authy_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, authy_id=None, password=None,
                    **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(
            email,
            authy_id,
            password,
            **extra_fields
        )

    def create_superuser(self, email, password,
                         **extra_fields):
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        user = self._create_user(
            email,
            None,
            password,
            **extra_fields
        )

        user.active = True
        user.sales = True
        user.admin = True
        user.save(using=self._db)
        return user
