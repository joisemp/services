from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        """
        Create and save a User with the given email or phone and password.
        """
        if not email and not phone:
            raise ValueError(_('The user must have either an email or a phone number.'))
        user = self.model(email=email, phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not email:
            raise ValueError(_('Superusers must have an email address.'))
        return self.create_user(email=email, password=password, **extra_fields)
