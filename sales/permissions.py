from rest_framework.permissions import BasePermission


class IsHellosignCallback(BasePermission):
    """
    Allows access only HelloSign callback.
    """

    def has_permission(self, request, view):
        if request.method == 'POST':
            necessary_headers = ['Content-Md5', 'Content-Sha256']

            user_agent = "HelloSign API"
            content_length = str(len(request.body))

            return bool(user_agent == request.headers.get('User-Agent') and
                        content_length == request.headers.get('Content-Length') and
                        all([1 if i in request.headers else 0 for i in necessary_headers]))
