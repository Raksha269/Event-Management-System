from rest_framework.authentication import SessionAuthentication


class EMSSessionAuthentication(SessionAuthentication):
    def authenticate_header(self, request):
        return "Session"
