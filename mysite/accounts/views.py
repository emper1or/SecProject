from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required,user_passes_test
from django.core.exceptions import PermissionDenied
from .forms import RegisterForm
from .models import CustomUser
from library.models import Book, BookCover
from .forms import RegisterForm, VerificationForm
from django.contrib import messages
from django.core.mail import send_mail #Импортируем функцию для отправки почты
from django.conf import settings
from django.contrib.auth import get_user_model
import requests
import logging



User = get_user_model()
logger = logging.getLogger(__name__) # Получаем логгер

def anonymous_required(user):
    return not user.is_authenticated


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Регистрация прошла успешно! Теперь войдите.')
            logger.info(f'Новый пользователь зарегистрирован: {user.username}')  # Логируем информацию о регистрации
            return redirect('login')
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
            return render(request, 'login.html', {'error': 'Неверное имя пользователя или пароль'})
    else:
        return render(request, 'login.html')


def send_verification_email(email, verification_code):
    """
    Отправляет письмо с кодом верификации на указанный email-адрес через SMTP Django.
    """
    subject = 'Код верификации'
    message = f'Ваш код верификации: {verification_code}'
    from_email = settings.DEFAULT_FROM_EMAIL # Email отправителя из настроек
    recipient_list = [email]
    html_message = f'<p>Ваш код верификации: <strong>{verification_code}</strong></p>' # Html версия

    try:
        logger.debug(f'Отправка email на {email}...')
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False, # False вызывает исключение при ошибке отправки
            html_message=html_message #Передаем html версию
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
                    messages.error(request, 'Превышено количество попыток верификации. Пожалуйста, повторите попытку позже.') #Можете перенаправить на страницу сброса пароля
                    return redirect('login') #Перенаправляем на страницу входа
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
    covers = BookCover.objects.filter(book__in=books)  # Получаем обложки для этих книг

    context = {
        'user': user,
        'books': books,
        'covers': covers,
    }
    return render(request, 'dashboard.html', context)


def home(request):
    return render(request, 'home.html')
