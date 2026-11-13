def axes_username(request, credentials):
    """The account name django-axes counts failures against: email for API logins, username for the admin form."""
    credentials = credentials or {}
    value = credentials.get("email") or credentials.get("username")
    if not value and request is not None:
        value = request.POST.get("username")
    return (value or "").strip().lower()
