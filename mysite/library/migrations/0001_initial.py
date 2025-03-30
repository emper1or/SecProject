import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Имя автора')),
                ('bio', models.TextField(blank=True, null=True, verbose_name='Биография автора')),
            ],
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Название книги')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Описание книги')),
                ('rating', models.IntegerField(blank=True, default=0, null=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='library.author', verbose_name='Автор')),
                ('users', models.ManyToManyField(related_name='books', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='BookCover',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cover', models.ImageField(blank=True, null=True, upload_to='covers/', verbose_name='Обложка книги')),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='library.book', verbose_name='Книга')),
            ],
        ),
    ]
