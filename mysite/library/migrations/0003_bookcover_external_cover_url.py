# Generated by Django 5.1.7 on 2025-04-26 02:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0002_book_review'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookcover',
            name='external_cover_url',
            field=models.URLField(blank=True, null=True, verbose_name='Внешняя обложка'),
        ),
    ]
