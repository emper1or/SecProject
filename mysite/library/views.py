from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import BookForm, BookCoverForm
from .models import Author, Book

@login_required
def add_author(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        bio = request.POST.get('bio')
        if name:  # Проверяем, что имя автора указано
            Author.objects.create(name=name, bio=bio)
            return redirect('add_book')  # Перенаправляем на страницу добавления книги
    return render(request, 'add_author.html')

@login_required
def add_book(request):
    authors = Author.objects.all()

    if request.method == 'POST':
        book_form = BookForm(request.POST)
        cover_form = BookCoverForm(request.POST, request.FILES)

        if book_form.is_valid() and cover_form.is_valid():
            # Создаем объект книги, но пока не сохраняем
            book = book_form.save(commit=False)
            book.author = book_form.cleaned_data['author']
            book.rating = book_form.cleaned_data.get('rating', 0)  # Устанавливаем 0, если рейтинг не передан
            book.save()

            # Добавляем текущего пользователя к книге (если в модели есть поле users)
            if hasattr(book, 'users'):
                book.users.add(request.user)

            # Сохраняем обложку, связывая с книгой
            cover = cover_form.save(commit=False)
            cover.book = book
            cover.save()

            return redirect('success')  # Перенаправление на страницу успеха
    else:
        book_form = BookForm()
        cover_form = BookCoverForm()

    return render(request, 'add_book.html', {
        'book_form': book_form,
        'cover_form': cover_form,
        'authors': authors,
    })


@login_required
def success(request):
    return render(request, 'success.html')
