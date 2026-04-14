from django.contrib.auth.models import User
from django.http import HttpRequest


class AuthedRequest(HttpRequest):
    """
    An HttpRequest whose `user` attribute is guaranteed to be an authenticated User.

    Use as the first-argument annotation on any django-ninja handler that requires
    auth. The narrowing is a contract, not runtime enforcement — pair this with
    ninja's `auth=` on the router or a middleware that rejects anonymous requests.
    """

    user: User  # type: ignore[assignment]
