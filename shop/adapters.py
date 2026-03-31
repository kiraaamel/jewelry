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
        Сохраняем пользователя со всеми полями из POST запроса.
        """
        # Сохраняем email и пароль
        user.email = form.cleaned_data.get('email')
        user.set_password(form.cleaned_data.get('password1'))
        
        # Сохраняем дополнительные поля из POST запроса
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.phone = request.POST.get('phone', '')
        
        if commit:
            user.save()
        return user