from typing import Any, Optional
from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from allauth.account.forms import SignupForm
from .models import User

# Валидатор для телефона
phone_validator: RegexValidator = RegexValidator(
    regex=r'^(\+7|7|8)?[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$',
    message='Введите корректный номер телефона в формате +7 999 123-45-67'
)


class CustomSignupForm(SignupForm):
    """
    Кастомная форма регистрации с валидацией телефона и email.

    Расширяет стандартную форму регистрации allauth, добавляя поля:
    - phone (обязательное поле с валидацией формата)
    - first_name (обязательное поле)
    - last_name (опциональное поле)

    Attributes:
        phone: Номер телефона пользователя.
        first_name: Имя пользователя.
        last_name: Фамилия пользователя (опционально).
    """

    phone = forms.CharField(
        max_length=20,
        required=True,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 999 123-45-67',
            'id': 'id_phone'
        }),
        error_messages={
            'required': 'Пожалуйста, укажите номер телефона',
            'invalid': 'Введите корректный номер телефона'
        }
    )

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_first_name'
        }),
        error_messages={
            'required': 'Пожалуйста, укажите ваше имя'
        }
    )

    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_last_name'
        })
    )

    def clean_email(self) -> str:
        """
        Проверка email на уникальность и корректность.

        Выполняет следующие проверки:
        1. Email не должен существовать в базе данных.
        2. Email должен содержать символ '@' и точку '.'.

        Returns:
            str: Очищенный и проверенный email.

        Raises:
            ValidationError: Если email уже существует или имеет неверный формат.
        """
        email: str = self.cleaned_data.get('email', '')

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')

        if '@' not in email or '.' not in email:
            raise forms.ValidationError('Введите корректный email адрес')

        return email

    def clean_phone(self) -> str:
        """
        Дополнительная проверка телефона.

        Удаляет все нецифровые символы и проверяет длину номера.

        Returns:
            str: Очищенный и проверенный номер телефона.

        Raises:
            ValidationError: Если номер телефона содержит неверное количество цифр.
        """
        phone: str = self.cleaned_data.get('phone', '')

        if phone:
            # Удаляем все нецифровые символы для проверки
            clean_phone: str = ''.join(filter(str.isdigit, phone))
            if len(clean_phone) not in [10, 11]:
                raise forms.ValidationError('Номер телефона должен содержать 10 или 11 цифр')

        return phone

    def save(self, request: HttpRequest) -> User:
        """
        Сохраняет пользователя с дополнительными полями.

        Args:
            request: HTTP-запрос, переданный при регистрации.

        Returns:
            User: Сохранённый экземпляр пользователя с заполненными полями
                  phone, first_name, last_name.
        """
        user: User = super().save(request)

        # Заполняем дополнительные поля
        user.phone = self.cleaned_data.get('phone', '')
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')

        user.save()

        return user