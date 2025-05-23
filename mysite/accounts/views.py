import logging
import re

from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from games.models import Game, GameCover
from library.models import Book, BookCover
from django.http import JsonResponse
import random
from .forms import RegisterForm, VerificationForm, ResetPasswordForm, PasswordChangeForm, UserEditForm
from .models import LoginAttempt
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

User = get_user_model()
logger = logging.getLogger(__name__)


def validate_username(request):
    username = request.GET.get('username', '').strip()
    response_data = {'is_valid': False}

    if not username:
        response_data['error'] = 'Имя пользователя не может быть пустым'
        return JsonResponse(response_data)

    if len(username) < 3:
        response_data['error'] = 'Имя пользователя должно содержать не менее 3 символов'
        return JsonResponse(response_data)

    if len(username) > 150:
        response_data['error'] = 'Имя пользователя должно содержать не более 150 символов'
        return JsonResponse(response_data)

    # Проверка допустимых символов
    allowed_chars = r'^[\w.@+-]+$'
    if not re.match(allowed_chars, username):
        response_data['error'] = 'Имя пользователя может содержать только буквы, цифры и символы @/./+/-/_'
        return JsonResponse(response_data)

    # Проверка существования пользователя
    if User.objects.filter(username__iexact=username).exists():
        response_data['error'] = 'Имя пользователя уже занято'
        return JsonResponse(response_data)

    response_data['is_valid'] = True
    return JsonResponse(response_data)


def validate_email(request):
    email = request.GET.get('email', '').strip()
    response_data = {'is_valid': False}

    if not email:
        response_data['error'] = 'Email не может быть пустым'
        return JsonResponse(response_data)

    try:
        validate_email(email)
    except ValidationError:
        response_data['error'] = 'Введите корректный email'
        return JsonResponse(response_data)

    # Проверка существования email
    if User.objects.filter(email__iexact=email).exists():
        response_data['error'] = 'Email уже используется'
        return JsonResponse(response_data)

    response_data['is_valid'] = True
    return JsonResponse(response_data)

def send_verification_email(email, verification_code):
    """Отправляет письмо с кодом верификации"""
    if settings.DEBUG:
        logger.debug(f'DEBUG mode: email НЕ отправляется. Код: {verification_code}, email: {email}')
        return

    try:
        subject = 'Код верификации'
        message = f'Ваш код верификации: {verification_code} (действителен 5 минут)'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        html_message = f'''
            <p>Ваш код верификации: <strong>{verification_code}</strong></p>
            <p>Код действителен в течение 5 минут.</p>
        '''

        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
            html_message=html_message
        )
        logger.info(f'Письмо успешно отправлено на {email}')
    except Exception as e:
        logger.error(f'Ошибка отправки письма на {email}: {e}')


def generate_verification_code():
    """Генерирует 6-значный код верификации"""
    return str(random.randint(100000, 999999))


def anonymous_required(user):
    return not user.is_authenticated


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            logger.info(f'Новый пользователь зарегистрирован: {user.username}')
            user.verification_code = generate_verification_code()
            user.verification_attempts = 0
            user.verification_code_sent_at = timezone.now()
            user.save()
            send_verification_email(user.email, user.verification_code)
            request.session['user_id'] = user.id

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('verify')
                })
            else:
                messages.info(request, 'На вашу электронную почту отправлен код подтверждения регистрации.')
                return redirect('verify')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field in form.errors:
                    errors[field] = form.errors[field]
                return JsonResponse({
                    'success': False,
                    'errors': errors
                }, status=400)
            else:
                return render(request, 'register.html', {'form': form})
    else:
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})


from datetime import datetime, timedelta
from django.core.cache import cache


def get_lockout_time(attempts):
    """Возвращает время блокировки в зависимости от количества попыток"""
    lockout_times = {
        3: timedelta(seconds=30),
        6: timedelta(minutes=1),
        9: timedelta(minutes=5),
        12: timedelta(minutes=15),
        15: timedelta(minutes=30),
        18: timedelta(hours=1),
        21: timedelta(hours=5),
    }

    # Находим максимальный порог, который был превышен
    applicable_thresholds = [th for th in lockout_times.keys() if attempts >= th]
    if not applicable_thresholds:
        return None

    max_threshold = max(applicable_thresholds)
    return lockout_times[max_threshold]


@user_passes_test(anonymous_required, login_url='home')
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        ip_address = request.META.get('REMOTE_ADDR')

        # Проверяем блокировку
        cache_key = f"login_lockout_{username}_{ip_address}"
        locked_until = cache.get(cache_key)

        if locked_until:
            if timezone.now() < locked_until:
                remaining_time = locked_until - timezone.now()
                return render(request, 'login.html', {
                    'error': f'Превышено количество попыток. Попробуйте снова через {int(remaining_time.total_seconds())} секунд.',
                    'username_value': username,
                    'is_locked': True,
                    'locked_until': locked_until
                })
            else:
                cache.delete(cache_key)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Сброс счетчика попыток при успешной аутентификации
            LoginAttempt.objects.filter(user=user, ip_address=ip_address).delete()
            cache.delete(cache_key)

            user.verification_code = generate_verification_code()
            user.verification_attempts = 0
            user.verification_code_sent_at = timezone.now()
            user.save()
            send_verification_email(user.email, user.verification_code)
            request.session['user_id'] = user.id
            return redirect('verify')
        else:
            # Увеличиваем счетчик попыток
            user = User.objects.filter(username=username).first()
            if user:
                attempt, created = LoginAttempt.objects.get_or_create(
                    user=user,
                    ip_address=ip_address,
                    defaults={'attempts': 1, 'last_attempt': timezone.now()}
                )
                if not created:
                    attempt.attempts += 1
                    attempt.last_attempt = timezone.now()
                    attempt.save()

                # Проверяем, нужно ли блокировать
                lockout_duration = get_lockout_time(attempt.attempts)
                if lockout_duration:
                    locked_until = timezone.now() + lockout_duration
                    attempt.locked_until = locked_until
                    attempt.save()
                    cache.set(cache_key, locked_until, timeout=int(lockout_duration.total_seconds()))

                    return render(request, 'login.html', {
                        'error': f'Неверное имя пользователя или пароль. Превышено количество попыток. Попробуйте снова через {int(lockout_duration.total_seconds())} секунд.',
                        'username_value': username,
                        'is_locked': True,
                        'locked_until': locked_until
                    })
                else:
                    return render(request, 'login.html', {
                        'error': f'Неверное имя пользователя или пароль. Попыток: {attempt.attempts}/3',
                        'username_value': username
                    })

            return render(request, 'login.html', {
                'error': 'Неверное имя пользователя или пароль',
                'username_value': username
            })
    else:
        return render(request, 'login.html')


def resend_code(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Сессия истекла. Пожалуйста, войдите снова.')
        return redirect('login')

    try:
        user = get_object_or_404(User, id=user_id)
        new_code = generate_verification_code()
        user.verification_code = new_code
        user.verification_attempts = 0
        user.verification_code_sent_at = timezone.now()
        user.save()
        send_verification_email(user.email, new_code)
        messages.success(request, 'Новый код верификации отправлен на вашу почту. Код действителен 5 минут.')
        return redirect('verify')
    except Exception as e:
        logger.error(f'Ошибка при повторной отправке кода: {e}')
        messages.error(request, 'Произошла ошибка при отправке кода. Пожалуйста, попробуйте снова.')
        return redirect('login')


def verify(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Сессия истекла. Пожалуйста, войдите снова.')
        return redirect('login')

    try:
        user = get_object_or_404(User, id=user_id)
        now = timezone.now()
        code_expired = (now - user.verification_code_sent_at) > timedelta(
            minutes=5) if user.verification_code_sent_at else True

        if code_expired or user.verification_attempts >= 3:
            user.verification_code = None
            user.save()
            code_expired = True

        if request.method == 'POST':
            form = VerificationForm(request.POST)
            if form.is_valid():
                code = form.cleaned_data['verification_code']

                if code_expired:
                    return render(request, 'verify.html', {
                        'form': form,
                        'remaining_attempts': 0,
                        'code_expired': True,
                        'error_message': 'Код недействителен. Пожалуйста, запросите новый код.'
                    })

                if user.verification_code == code:
                    user.reset_verification_attempts()
                    login(request, user)
                    del request.session['user_id']
                    return redirect('dashboard')
                else:
                    user.verification_attempts += 1
                    user.save()
                    remaining_attempts = 3 - user.verification_attempts

                    if user.verification_attempts >= 3:
                        user.verification_code = None
                        user.save()
                        return render(request, 'verify.html', {
                            'form': form,
                            'remaining_attempts': 0,
                            'code_expired': True,
                            'error_message': 'Превышено количество попыток. Код больше недействителен. Запросите новый код.'
                        })
                    else:
                        return render(request, 'verify.html', {
                            'form': form,
                            'remaining_attempts': remaining_attempts,
                            'error_message': f'Неверный код. Осталось попыток: {remaining_attempts}'
                        })
            else:
                return render(request, 'verify.html', {
                    'form': form,
                    'remaining_attempts': 3 - user.verification_attempts,
                    'code_expired': code_expired
                })
        else:
            form = VerificationForm()
            return render(request, 'verify.html', {
                'form': form,
                'remaining_attempts': 3 - user.verification_attempts if not code_expired else 0,
                'code_expired': code_expired
            })

    except Exception as e:
        logger.error(f'Ошибка при верификации: {e}')
        messages.error(request, 'Произошла ошибка при обработке запроса. Пожалуйста, попробуйте снова.')
        return redirect('login')


def logout_view(request):
    logout(request)
    return redirect('home')


from django.core.paginator import Paginator


@login_required
def dashboard(request):
    user = request.user

    # Получаем параметры пагинации из GET-запроса
    books_page_number = request.GET.get('books_page', 1)
    games_page_number = request.GET.get('games_page', 1)

    # Получаем все книги и игры пользователя
    all_books = Book.objects.filter(users=user).order_by('title')
    all_games = Game.objects.filter(users=user).order_by('title')

    # Создаем пагинаторы
    books_paginator = Paginator(all_books, 15)  # 15 книг на страницу
    games_paginator = Paginator(all_games, 15)  # 15 игр на страницу

    # Получаем текущие страницы
    books_page = books_paginator.get_page(books_page_number)
    games_page = games_paginator.get_page(games_page_number)

    book_covers = BookCover.objects.filter(book__in=books_page)
    game_covers = GameCover.objects.filter(game__in=games_page)

    context = {
        'user': user,
        'books_page': books_page,
        'games_page': games_page,
        'book_covers': book_covers,
        'game_covers': game_covers,
    }
    return render(request, 'dashboard.html', context)


def home(request):
    return render(request, 'home.html')


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first()

        if user:
            verification_code = generate_verification_code()
            user.verification_code = verification_code
            user.verification_code_sent_at = timezone.now()
            user.save()
            send_verification_email(email, verification_code)
            request.session['user_id'] = user.id
            messages.success(request, 'Код подтверждения отправлен на вашу почту.')
            return redirect('reset_password')
        else:
            messages.error(request, 'Пользователь с таким email не найден.')
            return render(request, 'forgot_password.html')

    return render(request, 'forgot_password.html')


def reset_password(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['verification_code']
            new_password = form.cleaned_data['password']

            if user.verification_code == code:
                user.set_password(new_password)
                user.verification_code = None
                user.save()

                # Сбрасываем все блокировки для этого пользователя
                LoginAttempt.objects.filter(user=user).delete()
                messages.success(request, 'Пароль успешно изменён! Теперь вы можете войти с новым паролем.')
                return redirect('login')
            else:
                form.add_error('verification_code', 'Неверный код подтверждения.')
    else:
        form = ResetPasswordForm()

    return render(request, 'reset_password.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'profile.html')


@login_required
def edit_profile(request):
    if request.method == 'POST':
        if 'delete_avatar' in request.POST:
            return delete_avatar(request)

        form = UserEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен.')
            return redirect('profile')
    else:
        form = UserEditForm(instance=request.user)
    return render(request, 'edit_profile.html', {'form': form})


@login_required
def delete_avatar(request):
    if request.method == 'POST':
        user = request.user
        if user.avatar:
            user.avatar = 'avatars/default_avatar.jpg'
            user.save()
            return JsonResponse({'success': True, 'message': 'Аватар успешно удален.'})
        else:
            return JsonResponse({'success': False, 'message': 'Аватар уже отсутствует.'}, status=400)
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password1']
            if request.user.check_password(old_password):
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Пароль успешно изменен.')
                return redirect('profile')
            else:
                form.add_error('old_password', 'Старый пароль введен неверно.')
    else:
        form = PasswordChangeForm()
    return render(request, 'change_password.html', {'form': form})
