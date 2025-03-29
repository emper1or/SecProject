from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .forms import DeveloperForm, GameForm, GameCoverForm
from .models import Developer, Game, GameCover


@login_required
def add_developer(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        bio = request.POST.get('bio')
        if name:  # Проверяем, что название разработчика указано
            Developer.objects.create(name=name, bio=bio)
            messages.success(request, 'Разработчик успешно добавлен!')
            return redirect('add_game')  # Перенаправляем на страницу добавления игры
    return render(request, 'games/add_developer.html')


@login_required
def add_game(request):
    developers = Developer.objects.all()
    initial_data = request.session.get('game_form_data', {})

    if request.method == 'POST':
        if 'add_developer' in request.POST:
            # Сохраняем введённые данные в сессию перед переходом
            request.session['game_form_data'] = request.POST.dict()
            return redirect('add_developer')

        game_form = GameForm(request.POST)
        cover_form = GameCoverForm(request.POST, request.FILES)

        if game_form.is_valid() and cover_form.is_valid():
            # Создаем объект игры, но пока не сохраняем
            game = game_form.save(commit=False)
            game.developer = game_form.cleaned_data['developer']
            game.rating = game_form.cleaned_data.get('rating', 0)
            game.save()

            # Добавляем текущего пользователя к игре
            if hasattr(game, 'users'):
                game.users.add(request.user)

            # Сохраняем обложку, связывая с игрой
            cover = cover_form.save(commit=False)
            cover.game = game
            cover.save()

            request.session.pop('game_form_data', None)
            messages.success(request, 'Игра успешно добавлена!')
            return redirect('game_success')  # Перенаправление на страницу успеха
    else:
        game_form = GameForm(initial=initial_data)
        cover_form = GameCoverForm()

    return render(request, 'games/add_game.html', {
        'game_form': game_form,
        'cover_form': cover_form,
        'developers': developers,
    })


@login_required
def game_success(request):
    return render(request, 'games/game_success.html')


@login_required
def game_detail(request, pk):
    game = get_object_or_404(Game, id=pk)
    covers = GameCover.objects.filter(game=game)
    return render(request, 'games/game_detail.html', {'game': game, 'covers': covers})


@login_required
def edit_game(request, pk):
    game = get_object_or_404(Game, id=pk)
    game_cover = game.gamecover_set.first()  # Получаем первую обложку игры

    if request.method == 'POST':
        game_form = GameForm(request.POST, instance=game)
        cover_form = GameCoverForm(request.POST, request.FILES, instance=game_cover)

        if game_form.is_valid() and cover_form.is_valid():
            game_form.save()

            # Если у игры уже есть обложка, удаляем её файл
            if 'cover' in cover_form.changed_data:
                covers = GameCover.objects.filter(game=game)
                for cover in covers:
                    cover.cover.delete()
                    cover.delete()

            # Сохраняем новую обложку
            cover = cover_form.save(commit=False)
            cover.game = game
            cover.save()

            return redirect('game_detail', pk=game.id)
    else:
        game_form = GameForm(instance=game)
        cover_form = GameCoverForm(instance=game_cover)

    return render(request, 'games/edit_game.html', {
        'game_form': game_form,
        'cover_form': cover_form,
        'game': game,
    })


@login_required
def delete_game(request, pk):
    game = get_object_or_404(Game, id=pk)
    if request.method == 'POST':
        covers = GameCover.objects.filter(game=game)
        for cover in covers:
            cover.cover.delete()
            cover.delete()
        game.delete()
        return redirect('dashboard')  # Или другой подходящий редирект
    return render(request, 'games/delete_game.html', {'game': game})