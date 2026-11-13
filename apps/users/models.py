from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Signs in with email. `username` stays as a display handle (it defaults to the email)."""

    email = models.EmailField("email address", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
