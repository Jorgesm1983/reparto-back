from django.urls import path, include
from .views import login_view, logout_view
from . import views

urlpatterns = [
    path('api/', include('api.urls')),
    path('api/login/', login_view, name='login'),
    path('api/logout/', logout_view, name='logout'),
    path('api/product/<int:product_id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('api/customer/<int:client_number>/', views.CustomerDetailView.as_view(), name='customer-detail'),
]
