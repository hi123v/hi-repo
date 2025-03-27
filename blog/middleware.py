from django.core.exceptions import PermissionDenied
from django.urls import resolve

class RestrictStudentAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.groups.filter(name='Student').exists():
            current_url = resolve(request.path_info).url_name
            if current_url == 'chat':
                raise PermissionDenied
        response = self.get_response(request)
        return response