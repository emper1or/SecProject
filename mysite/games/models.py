from django.db import models
from accounts.models import CustomUser


class Developer(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название разработчика")
    bio = models.TextField(verbose_name="Описание разработчика", blank=True, null=True)

    def __str__(self):
        return self.name


class Game(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название игры")
    description = models.TextField(verbose_name="Описание игры", blank=True, null=True)
    developer = models.ForeignKey(Developer, on_delete=models.CASCADE, verbose_name="Разработчик")
    users = models.ManyToManyField(CustomUser, related_name='games')
    rating = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return f"{self.title} (Рейтинг: {self.rating}/10)"


class GameCover(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, verbose_name="Игра")
    cover = models.ImageField(upload_to='game_covers/', blank=True, null=True, verbose_name="Обложка игры")

    def __str__(self):
        return f"Обложка для {self.game.title}"