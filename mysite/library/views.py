from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .utils import get_book_suggestions, get_book_details, get_author_info, get_book_details_isbn
from django.http import JsonResponse
from django.core.cache import cache
from django.views.decorators.cache import cache_page

from .forms import BookForm, BookCoverForm
from .models import Author, Book, BookCover

import requests
from django.core.files.base import ContentFile
import base64
import json

def clear_cache_for_book(book_id):
    """Удаляет все связанные с книгой ключи кэша"""
    cache.delete(f'book_detail_{book_id}')
    # Дополнительные ключи кэша, которые нужно очистить
    cache.delete_many([
        f'autocomplete_{book_id}',
        f'book_search_{book_id}',
    ])


@login_required
def add_author(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        bio = request.POST.get('bio', '')

        if name:
            author = Author.objects.create(name=name, bio=bio)
            request.session['book_form_data']['author'] = author.id
            messages.success(request, "Автор успешно добавлен!")
            return redirect('add_book')

    return render(request, 'add_author.html')


@login_required
def add_book(request):
    authors = Author.objects.all()
    initial_data = request.session.get('book_form_data', {})
    initial_rating = initial_data.get('rating', 5)
    initial_cover = request.session.get('book_cover', None)

    if request.method == 'POST':
        if 'add_author' in request.POST:
            request.session['book_form_data'] = request.POST.dict()
            request.session['book_cover'] = request.FILES.get('cover').name if 'cover' in request.FILES else None
            return redirect('add_author')

        book_form = BookForm(request.POST)
        cover_form = BookCoverForm(request.POST, request.FILES)

        if book_form.is_valid() and cover_form.is_valid():
            book = book_form.save(commit=False)
            book.author = book_form.cleaned_data['author']
            book.rating = book_form.cleaned_data.get('rating', 0)
            book.save()

            if hasattr(book, 'users'):
                book.users.add(request.user)

            cover = cover_form.save(commit=False)
            cover.book = book
            cover.save()

            request.session.pop('book_form_data', None)
            request.session.pop('book_cover', None)

            messages.success(request, 'Книга успешно добавлена!')
            return redirect('success')
    else:
        book_form = BookForm(initial=initial_data)
        cover_form = BookCoverForm()

    return render(request, 'add_book.html', {
        'book_form': book_form,
        'cover_form': cover_form,
        'authors': authors,
        'initial_rating': initial_rating,
        'initial_cover': initial_cover,
    })


@login_required
def success(request):
    return render(request, 'success.html')


@login_required
def book_details(request, pk):
    book = get_object_or_404(Book, id=pk)
    covers = BookCover.objects.filter(book=book)
    return render(request, 'book_detail.html', {'book': book, 'covers': covers})


@login_required
def edit_book(request, pk):
    book = get_object_or_404(Book, id=pk)
    book_cover = book.bookcover_set.first()

    if request.method == 'POST':
        book_form = BookForm(request.POST, instance=book)
        cover_form = BookCoverForm(request.POST, request.FILES, instance=book_cover)

        if book_form.is_valid() and cover_form.is_valid():
            book_form.save()

            if 'cover' in cover_form.changed_data:
                covers = BookCover.objects.filter(book=book)
                for cover in covers:
                    cover.cover.delete()
                    cover.delete()

            cover = cover_form.save(commit=False)
            cover.book = book
            cover.save()

            clear_cache_for_book(book.id)
            return redirect('book_details', pk=book.id)
    else:
        book_form = BookForm(instance=book)
        cover_form = BookCoverForm(instance=book_cover)

    return render(request, 'edit_book.html', {
        'book_form': book_form,
        'cover_form': cover_form,
        'book': book,
    })


@login_required
def delete_book(request, pk):
    book = get_object_or_404(Book, id=pk)
    if request.method == 'POST':
        covers = BookCover.objects.filter(book=book)
        for cover in covers:
            cover.cover.delete()
            cover.delete()
        book_id = book.id
        book.delete()
        clear_cache_for_book(book_id)
        return redirect('dashboard')
    return render(request, 'delete_book.html', {'book': book})


@cache_page(60 * 15)
def book_search(request):
    return render(request, 'search.html')


def autocomplete(request):
    query = request.GET.get('term', '')
    cache_key = f'autocomplete_{query}'
    suggestions = cache.get(cache_key)

    if not suggestions:
        suggestions = get_book_suggestions(query)
        cache.set(cache_key, suggestions, 60 * 15)

    return JsonResponse(suggestions, safe=False)


@cache_page(60 * 15)
def book_detail(request, book_id):
    cache_key = f'book_detail_{book_id}'
    book_data = cache.get(cache_key)
    print(book_data)
    if not book_data:
        if book_id.isdigit():
            book_data = get_book_details_isbn(book_id)
        else:
            book_data = get_book_details(book_id)
        cache.set(cache_key, book_data, 60 * 15)
    print(book_data)
    response = render(request, 'book_details_test.html', {'book': book_data})

    # Получаем текущие cookies или создаем пустой список
    recent_books = request.COOKIES.get('recent_books', '').split('|')
    recent_books = [b for b in recent_books if b]  # Удаляем пустые значения

    # Кодируем данные книги в base64 для безопасного хранения в cookies

    book_info = {
        'id': book_id,
        'title': book_data.get('title', ''),
        'cover': book_data.get('cover', '')
    }

    # Преобразуем в JSON и затем в base64
    book_info_json = json.dumps(book_info, ensure_ascii=False)
    book_info_encoded = base64.urlsafe_b64encode(book_info_json.encode('utf-8')).decode('ascii')

    # Обновляем список (удаляем дубликаты, если есть)
    if book_info_encoded in recent_books:
        recent_books.remove(book_info_encoded)
    recent_books.insert(0, book_info_encoded)

    # Ограничиваем количество книг
    recent_books = recent_books[:10]

    # Устанавливаем cookie на 30 дней
    response.set_cookie('recent_books', '|'.join(recent_books), max_age=24 * 60 * 60)

    if request.method == 'POST':
        authors_list = book_data.get('authors', [])
        if authors_list and authors_list[0]:
            author_name = authors_list[0]
            api_data = get_author_info(author_name)
            author, created = Author.objects.get_or_create(name=author_name, bio=api_data.get('bio'))
        else:
            author, created = Author.objects.get_or_create(name="Неизвестный автор")

        book, created = Book.objects.get_or_create(
            title=book_data.get('title'),
            defaults={
                'description': book_data.get('description'),
                'review': '',
                'rating': book_data.get('rating', 0),
                'author': author,
            }
        )

        if not created:
            book.description = book_data.get('description')
            book.review = ''
            book.rating = book_data.get('rating', 0)
            book.author = author
            book.save()

        if request.user.is_authenticated:
            book.users.add(request.user)

        if book_data.get('cover'):
            cover_url = book_data.get('cover')
            if cover_url.startswith(('http://', 'https://')):
                response = requests.get(cover_url)
                if response.status_code == 200:
                    cover, created = BookCover.objects.get_or_create(book=book)
                    cover.cover.save(
                        f"{book.title}_cover.jpg",
                        ContentFile(response.content)
                    )
                    cover.save()
            else:
                cover, created = BookCover.objects.get_or_create(
                    book=book,
                    defaults={'cover': cover_url}
                )
                if not created:
                    cover.cover = cover_url
                    cover.save()

        rating = request.POST.get('rating')
        review = request.POST.get('review')

        if rating:
            book.rating = int(rating)
        if review:
            book.review = review

        book.save()

        # Очищаем кэш для этой книги
        clear_cache_for_book(book_id)
        return render(request, 'book_details_test.html', {'book': book_data, 'saved': True})

    return response


def book_search_isbn(request):
    if request.method == 'POST':
        isbn = request.POST.get('isbn')
        return redirect('book_detail', book_id=isbn)
    # Получаем полные данные о книге
    return render(request, 'search_isbn.html')


@cache_page(60 * 15)
def author_detail(request, author_name):
    cache_key = f'author_detail_{author_name}'
    api_data = cache.get(cache_key)

    if not api_data:
        api_data = get_author_info(author_name)
        cache.set(cache_key, api_data, 60 * 15)

    context = {
        'author': {
            'name': author_name,
            'photo': api_data.get('photo'),
            'bio': api_data.get('bio'),
            'birth_date': api_data.get('birth_date'),
            'death_date': api_data.get('death_date'),
            'books_count': api_data.get('books_count', 0),
            'first_publication': api_data.get('first_publication')
        }
    }

    return render(request, 'author_detail_test.html', context)


def recent_books_view(request):
    recent_books = []
    if 'recent_books' in request.COOKIES:
        book_infos = request.COOKIES['recent_books'].split('|')

        for encoded_info in book_infos:
            if not encoded_info:
                continue

            try:
                decoded_info = base64.urlsafe_b64decode(encoded_info.encode('ascii')).decode('utf-8')
                book_info = json.loads(decoded_info)

                recent_books.append({
                    'id': book_info.get('id'),
                    'title': book_info.get('title'),
                    'cover': book_info.get('cover')
                })
            except (UnicodeError, json.JSONDecodeError, base64.binascii.Error):
                continue

    return render(request, 'recent_books.html', {'recent_books': recent_books})