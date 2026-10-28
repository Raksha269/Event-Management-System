from rest_framework.authentication import SessionAuthentication


class EMSSessionAuthentication(SessionAuthentication):
    """Session auth, but unauthenticated requests get 401 (not 403) so that
    'not logged in' and 'logged in but not allowed' are distinguishable."""

    def authenticate_header(self, request):
        return "Session"
