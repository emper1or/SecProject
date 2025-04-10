from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser
import re
from django.core.exceptions import ValidationError

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].label = 'Имя пользователя'
        self.fields['email'].label = 'Почта'
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'

        self.fields['username'].help_text = ('Не более 150 символов. \n'
                                             'Только буквы, цифры и @/./+/-/_.')
        self.fields['password1'].help_text = (
            'Ваш пароль должен содержать не менее 8 символов. \n'
            'Ваш пароль не может состоять только из цифр.'
        )
        self.fields['password2'].help_text = 'Повторите пароль для подтверждения.'

        def save(self, commit=True):
            user = super().save(commit=False)
            user.email = self.cleaned_data['email']
            if commit:
                user.save()
            return user


class VerificationForm(forms.Form):
    verification_code = forms.CharField(
        label="Код верификации",
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите шестизначный код',
            'inputmode': 'numeric',
            'pattern': '[0-9]*'
        }),
        help_text="Введите код из отправленного письма."
    )

    def clean_verification_code(self):
        code = self.cleaned_data.get("verification_code")
        if not code.isdigit():
            raise ValidationError("Код должен содержать только цифры.")
        if len(code) != 6:
            raise ValidationError("Код должен состоять из 6 цифр.")
        return code


class ResetPasswordForm(forms.Form):
    verification_code = forms.CharField(
        label="Код подтверждения",
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Код из email'}),
        help_text="Введите ваш код подтверждения с Вашей почты."
    )
    password = forms.CharField(
        label="Новый пароль",
        required=True,
        validators=[validate_password],
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Новый пароль'}),
        help_text="Пароль должен быть не менее 8 символов и содержать буквы и цифры."
    )
    confirm_password = forms.CharField(
        label="Подтвердите новый пароль",
        required=True,
        validators=[validate_password],
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите новый пароль'}),
        help_text="Введите новый пароль ещё раз для проверки."
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        # Проверка на совпадение паролей
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Пароли не совпадают!")

        return cleaned_data


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput,
        label="Старый пароль",
        help_text="Введите ваш текущий пароль для подтверждения."
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput,
        label="Новый пароль",
        validators=[validate_password],
        help_text="Пароль должен быть не менее 8 символов и содержать буквы и цифры."
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Подтвердите новый пароль",
        help_text="Введите новый пароль ещё раз для проверки."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("Новые пароли не совпадают.")
        return cleaned_data


class UserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'avatar']

    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.fields['avatar'].widget.attrs.update({'class': 'form-control'})
