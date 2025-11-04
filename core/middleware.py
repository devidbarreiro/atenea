from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs que no requieren login
        exempt_urls = [
            reverse('core:login'),
            reverse('core:logout'),
            reverse('core:signup'),
        ]

        if not request.user.is_authenticated and request.path not in exempt_urls:
            return redirect('core:login')

        return self.get_response(request)
