import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import User

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def send_password_reset_email(user_id: int) -> None:
    from .services import password_reset_link

    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return
    context = {"user": user, "reset_link": password_reset_link(user), "hours": settings.PASSWORD_RESET_TIMEOUT // 3600}
    send_mail(
        subject=render_to_string("users/emails/password_reset_subject.txt", context).strip(),
        message=render_to_string("users/emails/password_reset.txt", context),
        from_email=None,
        recipient_list=[user.email],
    )
    logger.info("Password reset email sent", extra={"user_id": user.pk})
