import uuid

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import User

EDITABLE_PROFILE_FIELDS = {"first_name", "last_name"}


class InvalidResetLink(Exception):
    pass


def register_user(*, email: str, password: str, first_name: str = "", last_name: str = "") -> User:
    email = email.strip().lower()
    user = User(
        email=email,
        username=email if len(email) <= 150 else uuid.uuid4().hex,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
    )
    validate_password(password, user)
    user.set_password(password)
    user.save()
    return user


def update_profile(*, user: User, **fields) -> User:
    changed = []
    for name, value in fields.items():
        if name in EDITABLE_PROFILE_FIELDS:
            setattr(user, name, value.strip() if isinstance(value, str) else value)
            changed.append(name)
    if changed:
        user.save(update_fields=changed)
    return user


def request_password_reset(*, email: str) -> None:
    """Queues a reset email if the account exists. Says nothing either way, so emails can't be probed."""
    from .tasks import send_password_reset_email

    user = User.objects.filter(email=email.strip().lower(), is_active=True).first()
    if user is not None:
        transaction.on_commit(lambda: send_password_reset_email.delay(user.pk))


def password_reset_link(user: User) -> str:
    from django.conf import settings

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"


def reset_password(*, uid: str, token: str, new_password: str) -> User:
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
        raise InvalidResetLink from exc
    if not default_token_generator.check_token(user, token):
        raise InvalidResetLink
    validate_password(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    sign_out_everywhere(user=user)
    return user


def change_password(*, user: User, new_password: str) -> None:
    validate_password(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    sign_out_everywhere(user=user)


def sign_out_everywhere(*, user: User) -> None:
    """Blacklists every refresh token the user holds; access tokens expire within minutes."""
    outstanding = OutstandingToken.objects.filter(user=user).exclude(blacklistedtoken__isnull=False)
    BlacklistedToken.objects.bulk_create([BlacklistedToken(token=t) for t in outstanding], ignore_conflicts=True)
