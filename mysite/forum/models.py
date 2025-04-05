from django.db import models
from django.conf import settings
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Topic(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='topics')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


class Message(models.Model):
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    # Поля для лайков/дизлайков
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='liked_messages',
        blank=True
    )
    dislikes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='disliked_messages',
        blank=True
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username}: {self.content[:50]}..."

class Vote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='votes')
    value = models.SmallIntegerField()  # 1 for like, -1 for dislike

    class Meta:
        unique_together = ('user', 'message')