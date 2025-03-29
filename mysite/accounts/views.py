import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail  # Импортируем функцию для отправки почты
from django.shortcuts import render, redirect, get_object_or_404

from games.models import Game, GameCover
from library.models import Book, BookCover

from .forms import RegisterForm, VerificationForm, ResetPasswordForm, PasswordChangeForm, UserEditForm

User = get_user_model()
logger = logging.getLogger(__name__)  # Получаем логгер


def anonymous_required(user):
    return not user.is_authenticated


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'На вашу электронную почту отправлен код подтверждения регистрации.')
            logger.info(f'Новый пользователь зарегистрирован: {user.username}')  # Логируем информацию о регистрации
            user.verification_code = user.generate_verification_code()
            user.verification_attempts = 0  # Reset attempts on new login
            user.save()
            send_verification_email(user.email, user.verification_code)
            request.session['user_id'] = user.id  # Store user ID in session
            return redirect('verify')
        else:

            return render(request, 'register.html', {'form': form})
    else:
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})


@user_passes_test(anonymous_required, login_url='home')
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Generate and send verification code
            user.verification_code = user.generate_verification_code()
            user.verification_attempts = 0  # Reset attempts on new login
            user.save()
            send_verification_email(user.email, user.verification_code)
            request.session['user_id'] = user.id  # Store user ID in session
            return redirect('verify')  # Redirect to verification page
        else:
            return render(request, 'login.html', {'error': 'Неверное имя пользователя или пароль', 'username_value': username})
    else:
        return render(request, 'login.html')


def send_verification_email(email, verification_code):
    """
    Отправляет письмо с кодом верификации на указанную почту только в режиме продакшен.
    """
    if settings.DEBUG:
        # Если Django работает в режиме разработки, просто логируем попытку отправки.
        logger.debug(f'DEBUG mode: email НЕ отправляется. Код: {verification_code}, email: {email}')
        return
    try:
        subject = 'Код верификации'
        message = f'Ваш код верификации: {verification_code}'
        from_email = settings.DEFAULT_FROM_EMAIL  # Email отправителя из настроек
        recipient_list = [email]
        html_message = f'<p>Ваш код верификации: <strong>{verification_code}</strong></p>'

        logger.debug(f'Отправка email на {email}...')
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,  # Exception при ошибке
            html_message=html_message
        )
        logger.info(f'Письмо успешно отправлено на {email}')
    except Exception as e:
        logger.error(f'Ошибка отправки письма на {email}: {e}')


def verify(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['verification_code']

            if user.verification_code == code:
                user.reset_verification_attempts()
                login(request, user)
                del request.session['user_id']  # Clear session
                return redirect('dashboard')
            else:
                user.verification_attempts += 1
                user.save()
                remaining_attempts = 3 - user.verification_attempts
                if user.verification_attempts >= 3:
                    messages.error(request,
                                   'Превышено количество попыток верификации. Пожалуйста, повторите попытку позже.')  #Можете перенаправить на страницу сброса пароля
                    return redirect('login')  #Перенаправляем на страницу входа
                else:
                    messages.error(request, f'Неверный код. Осталось попыток: {remaining_attempts}')
                    return render(request, 'verify.html', {'form': form, 'remaining_attempts': remaining_attempts})

    else:
        form = VerificationForm()
        return render(request, 'verify.html', {'form': form, 'remaining_attempts': 3 - user.verification_attempts})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    user = request.user
    books = Book.objects.filter(users=user)  # Получаем книги пользователя
    games = Game.objects.filter(users=user)  # Получаем игры пользователя
    book_covers = BookCover.objects.filter(book__in=books)  # Получаем обложки для книг
    game_covers = GameCover.objects.filter(game__in=games)  # Получаем обложки для игр

    context = {
        'user': user,
        'books': books,
        'games': games,
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
            verification_code = user.generate_verification_code()
            user.verification_code = verification_code
            user.save()
            send_verification_email(email, verification_code)
            request.session['user_id'] = user.id  # Сохраняем ID пользователя в сессии
            messages.success(request, 'Код подтверждения отправлен на вашу почту.')
            return redirect('reset_password')
        else:
            messages.error(request, 'Пользователь с таким email не найден.')
            return render(request, 'forgot_password.html')

    return render(request, 'forgot_password.html')

from django.contrib.auth.hashers import make_password

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
                messages.success(request, 'Пароль успешно изменён! Теперь вы можете войти с новым паролем.')
                return redirect('login')
            else:
                messages.error(request, 'Неверный код подтверждения.')
        else:
            for error in form.errors.values():
                messages.error(request, error)

    else:
        form = ResetPasswordForm()

    return render(request, 'reset_password.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'profile.html')


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен.')
            return redirect('profile')
    else:
        form = UserEditForm(instance=request.user)
    return render(request, 'edit_profile.html', {'form': form})


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
                update_session_auth_hash(request, request.user)  # Обновление сессии, чтобы пользователь не вышел
                messages.success(request, 'Пароль успешно изменен.')
                return redirect('profile')
            else:
                messages.error(request, 'Старый пароль введен неверно.')
    else:
        form = PasswordChangeForm()
    return render(request, 'change_password.html', {'form': form})
