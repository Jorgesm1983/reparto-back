from django.urls import path, include
from .views import login_view, logout_view, check_session, albaranes_pendientes, albaranes_tratados, albaranes_no_resueltos, update_failure, resend_email, email_failures, get_email_failure_reasons, count_pending_emails, unsatisfied_customers,update_unsatisfied_observation, count_unsatisfied_customers
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
    path('api/albaranes-pendientes/', albaranes_pendientes, name='albaranes-pendientes'),
    path('api/albaranes-tratados/', albaranes_tratados, name='albaranes-tratados'),
    path('api/albaranes-no-resueltos/', albaranes_no_resueltos, name='albaranes-no-resueltos'),
    path('api/email_failures/', email_failures, name='email_failures'),  # Añade esta línea
    path('api/update_failure/<int:failure_id>/', update_failure, name='update_failure'),
    path('api/resend_email/<int:failure_id>/', resend_email, name='resend_email'),
    path('api/email_failures/reasons/', get_email_failure_reasons, name='get_email_failure_reasons'),
    path('api/unsatisfied_customers/', unsatisfied_customers, name='unsatisfied_customers'),
    path('api/update_unsatisfied_observation/<int:delivery_id>/', update_unsatisfied_observation, name='update_unsatisfied_observation'),
    path('api/count_unsatisfied_customers/', count_unsatisfied_customers, name='count_unsatisfied_customers'),
    path('api/count_pending_emails/', count_pending_emails, name='count_pending_emails'),
]
