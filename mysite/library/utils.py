import requests
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_book_suggestions(query):
    """Получаем подсказки из Google Books API"""

    params = {
        "q": query,
        "langRestrict": "ru",
        "maxResults": 10,
        "fields": "items(id,volumeInfo/title,volumeInfo/authors)"
    }

    response = requests.get("https://www.googleapis.com/books/v1/volumes", params=params)
    data = response.json()

    suggestions = []
    for item in data.get('items', []):
        book_id = item['id']
        title = item['volumeInfo']['title']
        authors = ', '.join(item['volumeInfo'].get('authors', ['Автор неизвестен']))
        suggestions.append({
            'id': book_id,
            'text': f"{title} - {authors}"
        })

    return suggestions


def get_book_details(book_id):
    """Получаем детали книги по ID"""

    response = requests.get(f"https://www.googleapis.com/books/v1/volumes/{book_id}")
    data = response.json()

    volume_info = data.get('volumeInfo', {})
    authors = volume_info.get('authors', [])

    book_data = {
        'title': volume_info.get('title', ''),
        'authors': authors,
        'authors_str': ', '.join(authors),
        'published_date': volume_info.get('publishedDate', ''),
        'description': volume_info.get('description', ''),
        'cover': volume_info.get('imageLinks', {}).get('thumbnail', ''),
        'publisher': volume_info.get('publisher', ''),
        'page_count': volume_info.get('pageCount', ''),
        'categories':  volume_info.get('categories', ''),
        'first_author': authors[0] if authors else None  # Для ссылки на первого автора
    }


    return book_data


def get_author_info(author_name):
    """Получаем информацию об авторе из различных API"""

    # 1. Пробуем Wikipedia API (для биографии и фото)
    wiki_data = get_wikipedia_author_info(author_name)

    # 2. Пробуем OpenLibrary (для дат жизни)
    ol_data = get_openlibrary_author_info(author_name)

    # 3. Пробуем Google Books (для количества книг)
    gb_data = get_googlebooks_author_info(author_name)

    author_data = {
        'name': author_name,
        'bio': wiki_data.get('bio', ''),
        'photo': wiki_data.get('photo'),
        'birth_date': ol_data.get('birth_date'),
        'death_date': ol_data.get('death_date'),
        'books_count': gb_data.get('books_count', 0),
        'first_publication': gb_data.get('first_publication')
    }

    return author_data


def get_wikipedia_author_info(author_name):
    try:
        url = "https://ru.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'format': 'json',
            'titles': author_name,
            'prop': 'extracts|pageimages',
            'exintro': True,
            'explaintext': True,
            'pithumbsize': 300,
            'redirects': True
        }

        response = requests.get(url, params=params, timeout=3)
        data = response.json()
        page = next(iter(data['query']['pages'].values()))

        return {
            'bio': page.get('extract', ''),
            'photo': page.get('thumbnail', {}).get('source', '') if 'thumbnail' in page else None
        }
    except Exception as e:
        logger.error(f"Wikipedia API error for {author_name}: {str(e)}")
        return {}


def get_openlibrary_author_info(author_name):
    try:
        url = f"https://openlibrary.org/search/authors.json?q={author_name}"
        response = requests.get(url, timeout=3)
        data = response.json()

        if data['numFound'] > 0:
            author = data['docs'][0]
            return {
                'birth_date': author.get('birth_date'),
                'death_date': author.get('death_date')
            }
        return {}
    except Exception as e:
        logger.error(f"OpenLibrary API error for {author_name}: {str(e)}")
        return {}


def get_googlebooks_author_info(author_name):
    try:
        params = {
            "q": f"inauthor:{author_name}",
            "maxResults": 40,
            "langRestrict": "ru"
        }

        if hasattr(settings, 'GOOGLE_BOOKS_API_KEY'):
            params['key'] = settings.GOOGLE_BOOKS_API_KEY

        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params=params,
            timeout=3
        )
        data = response.json()

        items = data.get('items', [])
        pub_dates = [
            item['volumeInfo'].get('publishedDate', '9999')
            for item in items
            if 'publishedDate' in item['volumeInfo']
        ]

        return {
            'books_count': len(items),
            'first_publication': min(pub_dates) if pub_dates else None
        }
    except Exception as e:
        logger.error(f"Google Books API error for {author_name}: {str(e)}")
        return {}