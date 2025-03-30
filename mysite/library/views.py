from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .utils import get_book_suggestions, get_book_details, get_author_info
from django.http import JsonResponse

from .forms import BookForm, BookCoverForm
from .models import Author, Book, BookCover, Author_Test


@login_required
def add_author(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        bio = request.POST.get('bio', '')

        if name:
            author = Author.objects.create(name=name, bio=bio)
            request.session['book_form_data']['author'] = author.id  # Запоминаем нового автора
            messages.success(request, "Автор успешно добавлен!")
            return redirect('add_book')  # Возвращаемся на add_book без потери данных

    return render(request, 'add_author.html')


@login_required
def add_book(request):
    authors = Author.objects.all()

    # Получаем данные из сессии
    initial_data = request.session.get('book_form_data', {})
    initial_rating = initial_data.get('rating', 5)  # Значение по умолчанию
    initial_cover = request.session.get('book_cover', None)

    if request.method == 'POST':
        if 'add_author' in request.POST:
            # Сохраняем все данные перед переходом на страницу добавления автора
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

            # Сохраняем обложку
            cover = cover_form.save(commit=False)
            cover.book = book
            cover.save()

            # Очищаем сессию после успешного сохранения
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
def book_detail(request, pk):
    book = get_object_or_404(Book, id=pk)
    covers = BookCover.objects.filter(book=book)
    return render(request, 'book_detail.html', {'book': book, 'covers': covers})


@login_required
def edit_book(request, pk):
    book = get_object_or_404(Book, id=pk)

    # Получаем первую обложку книги (если она существует)
    book_cover = book.bookcover_set.first()

    if request.method == 'POST':
        book_form = BookForm(request.POST, instance=book)
        cover_form = BookCoverForm(request.POST, request.FILES, instance=book_cover)

        if book_form.is_valid() and cover_form.is_valid():
            book_form.save()

            # Если у книги уже есть обложка, удаляем её файл
            if 'cover' in cover_form.changed_data:
                covers = BookCover.objects.filter(book=book)
                for cover in covers:
                    cover.cover.delete()
                    cover.delete()

            # Сохраняем новую обложку
            cover = cover_form.save(commit=False)
            cover.book = book  # Связываем обложку с книгой
            cover.save()

            return redirect('book_detail', pk=book.id)
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
        book.delete()
        return redirect('dashboard')
    return render(request, 'delete_book.html', {'book': book})


def book_search(request):
    return render(request, 'search.html')


def autocomplete(request):
    query = request.GET.get('term', '')
    suggestions = get_book_suggestions(query)
    return JsonResponse(suggestions, safe=False)


def book_detail(request, book_id):
    # Получаем полные данные о книге
    book_data = get_book_details(book_id)
    return render(request, 'book_details_test.html', {'book': book_data})


# books/views.py

def author_detail(request, author_name):
    api_data = get_author_info(author_name)

    # Объединяем данные
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
