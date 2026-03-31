from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Адаптер для работы с кастомной моделью пользователя без username.
    """
    def populate_username(self, request, user):
        """
        Не заполняем username, так как его нет в модели.
        """
        pass

    def save_user(self, request, user, form, commit=True):
        """
        Сохраняем пользователя со всеми полями.
        """
        # Сохраняем email и пароль
        user.email = form.cleaned_data.get('email')
        user.set_password(form.cleaned_data.get('password1'))
        
        # Сохраняем дополнительные поля из формы
        user.first_name = form.cleaned_data.get('first_name', '')
        user.last_name = form.cleaned_data.get('last_name', '')
        user.phone = form.cleaned_data.get('phone', '')
        
        if commit:
            user.save()
        return user