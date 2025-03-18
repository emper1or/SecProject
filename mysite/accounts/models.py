from django.contrib.auth.models import AbstractUser
from django.core.validators import validate_email
from django.db import models
import random

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, validators=[validate_email])
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_attempts = models.IntegerField(default=0)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='customuser_set',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='customuser_set',
        related_query_name='user',
    )

    def generate_verification_code(self):
        return str(random.randint(100000, 999999))

    def reset_verification_attempts(self):
        self.verification_attempts = 0
        self.save()
