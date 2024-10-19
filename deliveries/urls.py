from django.urls import path, include
from .views import login_view, logout_view, check_session
from . import views

urlpatterns = [
    path('api/', include('api.urls')),
    path('api/login/', login_view, name='login'),
    path('api/logout/', logout_view, name='logout'),
    path('api/product/<int:product_id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('api/customer/<int:client_number>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    path('api/recent_deliveries/', views.recent_deliveries, name='recent_deliveries'),
    path('api/update_incident/<int:delivery_id>/', views.update_incident, name='update_incident'),
    path('api/check-session/', check_session, name='check-session'),
]
