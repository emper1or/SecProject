from django.contrib.auth.models import AbstractUser
from django.core.validators import validate_email
from django.db import models
import random

def user_avatar_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/avatar/<filename>
    return f'user_{instance.id}/avatar/{filename}'

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, validators=[validate_email])
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_attempts = models.IntegerField(default=0)
    verification_code_sent_at = models.DateTimeField(blank=True, null=True)
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=False,
        verbose_name='Аватар',
        default='avatars/default_avatar.jpg'
    )

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
        self.verification_code = None
        self.verification_attempts = 0
        self.verification_code_sent_at = None
        self.save()


class LoginAttempt(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='login_attempts')
    ip_address = models.GenericIPAddressField()
    attempts = models.PositiveIntegerField(default=0)
    last_attempt = models.DateTimeField(auto_now=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'ip_address')

    def __str__(self):
        return f"{self.user.username} - {self.ip_address} - {self.attempts} attempts"