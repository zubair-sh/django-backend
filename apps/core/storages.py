from django.conf import settings
from storages.backends.s3 import S3Storage


class StaticStorage(S3Storage):
    """Static files live under static/ in the bucket and are served by CloudFront, whose origin path is /static."""

    location = "static"
    default_acl = None
    querystring_auth = False
    file_overwrite = True

    def url(self, name, parameters=None, expire=None, http_method=None):
        return f"https://{settings.CDN_DOMAIN}/{name.lstrip('/')}"
