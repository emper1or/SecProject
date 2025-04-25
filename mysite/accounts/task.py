from datetime import timedelta
from django.utils import timezone
from .models import LoginAttempt
from django.core.cache import cache


def cleanup_login_attempts():
    """Очищает старые записи о попытках входа (старше 24 часов)"""
    cutoff = timezone.now() - timedelta(hours=24)
    LoginAttempt.objects.filter(last_attempt__lt=cutoff).delete()

    # Также можно очистить соответствующие кэшированные блокировки
    # (это будет работать, если используется префикс 'login_lockout_')
    for key in cache.keys('login_lockout_*'):
        cache.delete(key)