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

    class Meta:
        model = Delivery
        fields = ['fiscal_year', 'delivery_number', 'client_conformity', 'has_issue', 'observations', 'delivery_images', 'issue_photos']

    def create(self, validated_data):
        delivery_images = validated_data.pop('delivery_images', [])
        issue_photos = validated_data.pop('issue_photos', [])
        issues = validated_data.pop('issues', [])
        
        delivery = super().create(validated_data)
        
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

