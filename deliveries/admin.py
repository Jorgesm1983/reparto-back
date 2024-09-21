# from django.contrib import admin
# from .models import Delivery, DeliveryImage, IssuePhoto

# @admin.register(Delivery)
# class DeliveryAdmin(admin.ModelAdmin):
#     list_display = ('fiscal_year', 'delivery_number', 'client_conformity', 'has_issue')
#     fields = ('fiscal_year', 'delivery_number', 'client_conformity', 'has_issue', 'observations', 'issues', 'delivery_images', 'issue_photos')
#     filter_horizontal = ('delivery_images', 'issue_photos')

# @admin.register(DeliveryImage)
# class DeliveryImageAdmin(admin.ModelAdmin):
#     list_display = ('id', 'image')

# @admin.register(IssuePhoto)
# class IssuePhotoAdmin(admin.ModelAdmin):
#     list_display = ('id', 'image')  # Agrega el número de producto aquí si existe en el modelo
   
   
from django.contrib import admin
from .models import Delivery, DeliveryImage, IssuePhoto

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('user', 'fiscal_year', 'delivery_number', 'client_number', 'visit_type', 'client_conformity', 'issues', 'has_issue', 'is_resolved', 'created_at', 'updated_at')
    fields = ('fiscal_year', 'delivery_number', 'client_number', 'visit_type', 'client_conformity', 'has_issue', 'observations', 'issues', 'is_resolved', 'delivery_images', 'issue_photos')
    filter_horizontal = ('delivery_images', 'issue_photos')
    list_filter = ('visit_type', 'client_conformity', 'has_issue', 'is_resolved', 'created_at')
    search_fields = ('client_number', 'fiscal_year', 'delivery_number')

@admin.register(DeliveryImage)
class DeliveryImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image')

@admin.register(IssuePhoto)
class IssuePhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'image')  # Si quieres mostrar un campo adicional, como el número de producto, debes agregarlo aquí.



