from .models import User

EDITABLE_PROFILE_FIELDS = {"first_name", "last_name"}


def update_profile(*, user: User, **fields) -> User:
    changed = []
    for name, value in fields.items():
        if name in EDITABLE_PROFILE_FIELDS:
            setattr(user, name, value.strip() if isinstance(value, str) else value)
            changed.append(name)
    if changed:
        user.save(update_fields=changed)
    return user
