from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Модель пользователя.
    """
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Телефон'
    )
    bonus_points = models.IntegerField(
        default=0,
        verbose_name='Бонусные баллы'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email