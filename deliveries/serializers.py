# from rest_framework import serializers
# from .models import Delivery, DeliveryImage, IssuePhoto

# class DeliveryImageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DeliveryImage
#         fields = ['id', 'image']

# class IssuePhotoSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = IssuePhoto
#         fields = ['id', 'image']

# class DeliverySerializer(serializers.ModelSerializer):
#     delivery_images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)
#     issue_photos = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)

#     class Meta:
#         model = Delivery
#         fields = ['fiscal_year', 'delivery_number', 'client_conformity', 'has_issue', 'observations', 'delivery_images', 'issue_photos']

#     def create(self, validated_data):
#         delivery_images = validated_data.pop('delivery_images', [])
#         issue_photos = validated_data.pop('issue_photos', [])
        
#         delivery = super().create(validated_data)
        
#         for image in delivery_images:
#             delivery_image = DeliveryImage.objects.create(image=image)
#             delivery.delivery_images.add(delivery_image)
        
#         if delivery.has_issue:
#             for photo in issue_photos:
#                 issue_photo = IssuePhoto.objects.create(image=photo)
#                 delivery.issue_photos.add(issue_photo)
        
#         return delivery

###############################################################################

# 

from rest_framework import serializers
from .models import Delivery, DeliveryImage, IssuePhoto
import json

class DeliveryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryImage
        fields = ['id', 'image']

class IssuePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssuePhoto
        fields = ['id', 'image']

class DeliverySerializer(serializers.ModelSerializer):
    delivery_images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)
    issue_photos = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)
    issues = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True) # Agrega este campo# Agrega esta línea para el campo `issues`
    client_number = serializers.IntegerField(write_only=True)  
    visit_type = serializers.ChoiceField(choices=Delivery.VISIT_TYPE_CHOICES, required=True)
    is_resolved = serializers.BooleanField(required=False)

    class Meta:
        model = Delivery
        fields = ['client_number', 'fiscal_year', 'delivery_number', 'client_conformity', 'has_issue', 'observations', 'delivery_images', 'issue_photos', 'issues', 'visit_type', 'is_resolved']

    def validate_issues(self, value):
        print("Valor de issues en validación:", value)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("El campo issues debe ser una lista de números enteros.")
        
        if not isinstance(value, list):
            raise serializers.ValidationError("El campo issues debe ser una lista.")
        if any(not isinstance(issue, int) for issue in value):
            raise serializers.ValidationError("Cada valor en issues debe ser un número entero.")
        return value

    def create(self, validated_data):
        client_number = validated_data.pop('client_number')
        delivery_images = validated_data.pop('delivery_images', [])
        issue_photos = validated_data.pop('issue_photos', [])
        issues = validated_data.pop('issues', [])
        
        delivery = Delivery.objects.create(client_number=client_number, **validated_data)
        
    # if request.data.get('form_type') == 'verificacion' or request.data.get('form_type') == 'resolucion':
    # # Evitar que el campo 'issues' sea validado para estos formularios
    #     data.pop('issues', None)
        
        
        # Si hay problemas, almacénalos
        if issues:
            delivery.issues = issues
            delivery.save()
        
        for image in delivery_images:
            delivery_image = DeliveryImage.objects.create(image=image, delivery=delivery)
            delivery.delivery_images.add(delivery_image)
        
        if delivery.has_issue:
            for photo in issue_photos:
                issue_photo = IssuePhoto.objects.create(image=photo, delivery=delivery)
                delivery.issue_photos.add(issue_photo)
        
        return delivery

