from typing import Any, Dict, Optional
from django.http import HttpRequest
from django.contrib.auth.models import AbstractBaseUser  # Для type hinting user
from allauth.account.adapter import DefaultAccountAdapter
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Адаптер для работы с кастомной моделью пользователя без username.

    Переопределяет методы populate_username и save_user для корректной
    работы с моделью, где отсутствует поле username, но есть email, phone,
    first_name, last_name.
    """

    def populate_username(self, request: HttpRequest, user: AbstractBaseUser) -> None:
        """
        Не заполняем username, так как его нет в модели.

        В родительском методе DefaultAccountAdapter.populate_username обычно
        генерируется username из email или других полей. Поскольку кастомная
        модель пользователя не имеет поля username, этот метод переопределён
        как пустая операция (pass).

        Args:
            request: HTTP-запрос от клиента
            user: Экземпляр модели пользователя (без поля username)
        """
        # Нет поля username — ничего не делаем
        pass

    def save_user(self, request: HttpRequest, user: AbstractBaseUser,
                  form: Any, commit: bool = True) -> AbstractBaseUser:
        """
        Сохраняем пользователя со всеми полями из POST запроса.

        Вся валидация уже выполнена в форме, здесь просто сохраняем.
        Поля берутся из form.cleaned_data. Пароль хешируется через
        user.set_password().

        Args:
            request: HTTP-запрос (содержит данные формы)
            user: Экземпляр модели пользователя (ещё не сохранённый в БД)
            form: Форма регистрации (обычно allauth.forms.SignupForm)
            commit: Если True — сразу сохраняем в БД, иначе возвращаем
                    объект без сохранения

        Returns:
            AbstractBaseUser: Сохранённый или несохранённый экземпляр пользователя

        Note:
            Поле phone считается строковым и может быть пустым.
            Пароль обязательно должен быть установлен через set_password(),
            иначе пользователь не сможет войти.
        """
        # Безопасное извлечение данных из очищенного словаря формы
        user.email = form.cleaned_data.get('email', '')  # type: ignore[assignment]
        user.set_password(form.cleaned_data.get('password1', ''))
        user.first_name = form.cleaned_data.get('first_name', '')  # type: ignore[attr-defined]
        user.last_name = form.cleaned_data.get('last_name', '')  # type: ignore[attr-defined]
        user.phone = form.cleaned_data.get('phone', '')  # type: ignore[attr-defined]

        if commit:
            user.save()  # type: ignore[attr-defined]
        return user