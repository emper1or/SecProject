# books/management/commands/import_authors.py
from django.core.management.base import BaseCommand
from library.models import Author, Book
from library.utils import get_book_details


class Command(BaseCommand):
    help = 'Импорт авторов из существующих книг'

    def handle(self, *args, **options):
        for book in Book.objects.all():
            if not book.authors.exists():
                # Получаем данные книги из API
                book_data = get_book_details(book.google_books_id)

                for author_name in book_data.get('authors', []):
                    author, created = Author.objects.get_or_create(name=author_name)
                    book.authors.add(author)

                self.stdout.write(f'Добавлены авторы для книги: {book.title}')
