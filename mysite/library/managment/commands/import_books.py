from django.core.management.base import BaseCommand
from library.models import Book
from library.utils import fetch_books_from_google


class Command(BaseCommand):
    help = "Импорт книг из Google Books API"

    def add_arguments(self, parser):
        parser.add_argument("query", type=str, help="Поисковый запрос (название или автор)")

    def handle(self, *args, **options):
        query = options["query"]
        books_data = fetch_books_from_google(query)

        for item in books_data:
            volume_info = item.get("volumeInfo", {})
            Book.objects.get_or_create(
                title=volume_info.get("title", "Без названия"),
                defaults={
                    "author": ", ".join(volume_info.get("authors", [])),
                    "description": volume_info.get("description", ""),
                    "published_date": volume_info.get("publishedDate", ""),
                    "isbn": volume_info.get("industryIdentifiers", [{}])[0].get("identifier", ""),
                    "cover_url": volume_info.get("imageLinks", {}).get("thumbnail", ""),
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Импортировано {len(books_data)} книг!"))
