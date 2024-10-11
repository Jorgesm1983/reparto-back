from rest_framework import serializers
from .models import Delivery, DeliveryImage, IssuePhoto, Customer
from django.utils import timezone
import json

class DeliveryImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = DeliveryImage
        fields = ['url', 'image']
    def get_url(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None




class IssuePhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = IssuePhoto
        fields = ['url', 'image']
    def get_url(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None

class DeliverySerializer(serializers.ModelSerializer):
    
    delivery_images = DeliveryImageSerializer(
        source='delivery_image_set', many=True, read_only=True
    )
    uploaded_delivery_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    issue_photos = IssuePhotoSerializer(
        source='issue_photo_set', many=True, read_only=True
    )
    uploaded_issue_photos = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    issues = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True) # Agrega este campo# Agrega esta línea para el campo `issues`
    client_number = serializers.IntegerField(write_only=True)  # Permite enviar el número de cliente al crear o actualizar
    client_number_display = serializers.SerializerMethodField()  # Para mostrar el número de cliente en la respuesta
    customer_name = serializers.SerializerMethodField()  # Para obtener el nombre del cliente
    visit_type = serializers.ChoiceField(choices=Delivery.VISIT_TYPE_CHOICES, required=True)
    is_resolved = serializers.BooleanField(required=False)
    status = serializers.ChoiceField(choices=Delivery.STATUS_CHOICES, required=True)
    

    class Meta:
        model = Delivery
        fields = ['id','client_number','client_number_display','uploaded_delivery_images','uploaded_issue_photos','customer_name', 'fiscal_year', 'delivery_number', 'client_conformity', 'has_issue', 'observations', 'delivery_images', 'issue_photos', 'issues', 'visit_type', 'is_resolved', 'status','created_at']

        extra_kwargs = {
            'client_number': {'write_only': True},
            'uploaded_images': {'write_only': True},  # Este campo es solo para recibir imágenes en la creación
        }
    def get_client_number_display(self, obj):
        # Verifica si el objeto `customer` está definido y devuelve su número de cliente
        return obj.customer.client_number if obj.customer else None
    def get_customer_name(self, obj):
        return obj.customer.name if obj.customer else "Desconocido"

    def validate_issues(self, value):
        # print("Valor de issues en validación:", value)
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
    # Extraer los datos necesarios
        client_number = validated_data.pop('client_number')
        uploaded_delivery_images = validated_data.pop('uploaded_delivery_images', [])
        uploaded_issue_photos = validated_data.pop('uploaded_issue_photos', [])
        issues = validated_data.pop('issues', [])
        
        # Buscar el cliente por número de cliente, si no se encuentra, el cliente será None
        customer = Customer.objects.filter(client_number=client_number).first()

        # Asegúrate de que 'customer' no esté en validated_data para evitar conflictos
        validated_data.pop('customer', None)

        # Crear la entrega, incluyendo el número de cliente y el cliente asociado (si lo hay)
        delivery = Delivery.objects.create(
            customer=customer,
            client_number=client_number,
            **validated_data
        )

        # Si hay problemas, almacenarlos
        if issues:
            delivery.issues = issues
            delivery.save()

        # Guardar imágenes de entrega
        for image in uploaded_delivery_images:
            DeliveryImage.objects.create(delivery=delivery, image=image)
            
        for photo in uploaded_issue_photos:
            IssuePhoto.objects.create(delivery=delivery, image=photo)

        # Guardar fotos de incidencias o resoluciones no finalizadas
        if delivery.visit_type in ['verification', 'resolution'] or delivery.has_issue:
            for photo in uploaded_issue_photos:
                print(f"Guardando foto de incidencia: {photo}")
                IssuePhoto.objects.create(delivery=delivery, image=photo)
        

        return delivery
