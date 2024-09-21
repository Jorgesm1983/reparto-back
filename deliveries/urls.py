from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('api/', include('api.urls')),
    path('api/login/', obtain_auth_token, name='login'),  # Ruta para el login
]
