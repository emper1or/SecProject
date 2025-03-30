from django.db import models
from accounts.models import CustomUser

class Author(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя автора")
    bio = models.TextField(verbose_name="Биография автора", blank=True, null=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название книги")
    description = models.TextField(verbose_name="Описание книги", blank=True, null=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, verbose_name="Автор")
    users = models.ManyToManyField(CustomUser, related_name='books')
    rating = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return f"{self.title} (Рейтинг: {self.rating}/10)"


class BookCover(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="Книга")
    cover = models.ImageField(upload_to='covers/', blank=True, null=True, verbose_name="Обложка книги")
    def __str__(self):
        return f"Обложка для {self.book.title}"


class Author_Test(models.Model):
    name = models.CharField("Имя автора", max_length=200, unique=True)
    bio = models.TextField("Биография", blank=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)
    death_date = models.DateField("Дата смерти", null=True, blank=True)
    photo = models.URLField("Фото", blank=True)

    def __str__(self):
        return self.name



