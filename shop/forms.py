from django import forms
from allauth.account.forms import SignupForm
from django.core.validators import RegexValidator


class CustomSignupForm(SignupForm):
    """
    Кастомная форма регистрации с дополнительными полями.
    """
    first_name = forms.CharField(
        max_length=30, 
        required=False, 
        label='Имя'
    )
    last_name = forms.CharField(
        max_length=30, 
        required=False, 
        label='Фамилия'
    )
    phone = forms.CharField(
        max_length=20, 
        required=False, 
        label='Телефон',
        validators=[
            RegexValidator(
                regex=r'^\+?7?\d{10,15}$',
                message='Введите корректный номер телефона (например, +79161234567 или 89161234567)'
            )
        ]
    )

    def save(self, request):
        """
        Сохраняем пользователя с дополнительными полями.
        """
        user = super().save(request)
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.phone = self.cleaned_data.get('phone', '')
        user.save()
        return user