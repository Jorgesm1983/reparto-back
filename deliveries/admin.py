from django.contrib import admin
from .models import Delivery, DeliveryImage, IssuePhoto

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('fiscal_year', 'delivery_number', 'client_conformity', 'has_issue')
    fields = ('fiscal_year', 'delivery_number', 'client_conformity', 'has_issue', 'observations', 'issues', 'delivery_images', 'issue_photos')
    filter_horizontal = ('delivery_images', 'issue_photos')

@admin.register(DeliveryImage)
class DeliveryImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image')

@admin.register(IssuePhoto)
class IssuePhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'image')


