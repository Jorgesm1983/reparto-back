from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from . import views

urlpatterns = [
    path('api/', include('api.urls')),
    path('api/login/', obtain_auth_token, name='login'),  # Ruta para el login
    path('api/product/<int:product_id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('api/customer/<int:client_number>/', views.CustomerDetailView.as_view(), name='customer-detail'),
]
