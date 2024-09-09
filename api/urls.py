from django.urls import path
from deliveries.views import DeliveryCreateView

urlpatterns = [
    path('deliveries/', DeliveryCreateView.as_view(), name='create-delivery'),
]

