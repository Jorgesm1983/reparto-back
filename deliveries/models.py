# from django.db import models
# # import uuid
# import os


# def create_folder(path):
#     if not os.path.exists(path):
#         os.makedirs(path)
        
# def upload_to(instance, filename, folder_name):
#     # Conserva el nombre original del archivo
#     file_path = os.path.join(folder_name, filename)
#     # Asegúrate de que la carpeta existe
#     create_folder(os.path.dirname(file_path))
#     return file_path
        
# # def upload_to(instance, filename, folder_name):
# #     ext = filename.split('.')[-1]
# #     new_filename = f"{uuid.uuid4().hex}.{ext}"
# #     return os.path.join(folder_name, new_filename)

# class Delivery(models.Model):
#     fiscal_year = models.CharField(max_length=4)
#     delivery_number = models.PositiveIntegerField()
#     client_conformity = models.BooleanField(default=True)
#     has_issue = models.BooleanField(default=False)
#     observations = models.TextField(blank=True, null=True)
#     issues = models.JSONField(default=list)
#     # delivery_image = models.ImageField(upload_to='deliveries/', blank=True, null=True)  # Nuevo campo para imágenes
#     delivery_images = models.ManyToManyField('DeliveryImage', blank=True)
#     issue_photos = models.ManyToManyField('IssuePhoto', blank=True)
    
# def get_delivery_path(self):
#         folder_name = f"{instance.year}/{instance.albaran}"
#         return f"{self.fiscal_year}_{self.delivery_number}"

# def __str__(self):
#         folder_name = f"{instance.year}/{instance.albaran}"
#         return f"Albarán {self.fiscal_year}/{self.delivery_number}"
         
# #nuevo
# def save(self, *args, **kwargs):
#         # Código para gestionar las imágenes si es necesario
#         super().save(*args, **kwargs)

# class DeliveryImage(models.Model):
#     image = models.ImageField(upload_to=lambda instance, filename: upload_to(instance, filename, f'deliveries/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}'))

#     # Si DeliveryImage no tiene relación directa con Delivery, este método no es necesario

# class IssuePhoto(models.Model):
#     image = models.ImageField(upload_to=lambda instance, filename: upload_to(instance, filename, f'issues/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}'))

# from django.db import models
# import os

################################################################

# import os
# import re
# from django.db import models
# from django.core.files.storage import default_storage

# def get_incremental_filename(folder_path, base_filename):
#     """Genera un nombre de archivo único en base a un nombre base y una carpeta."""
#     i = 1
#     while True:
#         filename = f"{base_filename}_{i}"
#         file_path = os.path.join(folder_path, f"{filename}.jpg")  # Asume .jpg, cambiar según tipo de archivo
#         if not os.path.exists(file_path):
#             return f"{filename}.jpg"
#         i += 1




# def upload_to(instance, filename, folder_name):
#     # Conserva el nombre original del archivo
#     return os.path.join(folder_name, filename)

# class Delivery(models.Model):
#     fiscal_year = models.CharField(max_length=4)
#     delivery_number = models.PositiveIntegerField()
#     client_conformity = models.BooleanField(default=True)
#     has_issue = models.BooleanField(default=False)
#     observations = models.TextField(blank=True, null=True)
#     issues = models.JSONField(default=list)
#     # delivery_image = models.ImageField(upload_to='deliveries/', blank=True, null=True)  # Comentado, no se usa aquí
#     delivery_images = models.ManyToManyField('DeliveryImage', blank=True)
#     issue_photos = models.ManyToManyField('IssuePhoto', blank=True)
    
#     def __str__(self):
#         return f"Albarán {self.fiscal_year}/{self.delivery_number}"

# class DeliveryImage(models.Model):
#     image = models.ImageField(upload_to=lambda instance, filename: upload_to(instance, filename, f'deliveries/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}'))

# class IssuePhoto(models.Model):
#     image = models.ImageField(upload_to=lambda instance, filename: upload_to(instance, filename, f'issues/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}'))


import os
from django.db import models
from django.core.files.storage import default_storage
from django.contrib.auth.models import User
from django.utils import timezone

def get_incremental_filename(folder_path, base_filename, file_ext):
    """Genera un nombre de archivo único en base a un nombre base y una carpeta."""
    i = 1
    while True:
        filename = f"{base_filename}_{i}"
        file_path = os.path.join(folder_path, f"{filename}{file_ext}")
        if not os.path.exists(file_path):
            return f"{filename}{file_ext}"
        i += 1

def upload_to(instance, filename, folder_name):
    """Genera la ruta de almacenamiento del archivo, asegurando un nombre único."""
    base_name, file_ext = os.path.splitext(filename)
    folder_path = os.path.join('media', folder_name)
    base_filename = f"{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}"
    new_filename = get_incremental_filename(folder_path, base_filename, file_ext)
    full_folder_path = os.path.join('media', folder_name)
    if not os.path.exists(full_folder_path):
        os.makedirs(full_folder_path)
        print(f"Carpeta creada: {full_folder_path}")

    return os.path.join(folder_name, new_filename)

def get_delivery_image_upload_to(instance, filename):
    """Genera la ruta de almacenamiento para las imágenes de entrega."""
    return upload_to(instance, filename, f'deliveries/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}')

def get_issue_photo_upload_to(instance, filename):
    """Genera la ruta de almacenamiento para las fotos de incidencias."""
    return upload_to(instance, filename, f'issues/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}')

class Delivery(models.Model):
    VISIT_TYPE_CHOICES = [
        ('delivery', 'Entrega'),
        ('verification', 'Verificación'),
        ('resolution', 'Resolución'),
    ]
    
    # Relación con el cliente
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, null=True, blank=True)  # Relaciona la entrega con el cliente
    
    # Relación con el usuario que registra la entrega
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Relaciona la entrega con el usuario autenticado

    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE_CHOICES, default='delivery')
    client_number = models.PositiveIntegerField()  # Almacena el número del cliente directamente
    fiscal_year = models.CharField(max_length=4)
    delivery_number = models.PositiveIntegerField()
    client_conformity = models.BooleanField(default=True)
    has_issue = models.BooleanField(default=False)
    observations = models.TextField(blank=True, null=True)
    issues = models.JSONField(default=list, blank=True)
    is_resolved = models.BooleanField(default=False)  # Nuevo campo para indicar si la incidencia está resuelta
    delivery_images = models.ManyToManyField('DeliveryImage', blank=True)
    issue_photos = models.ManyToManyField('IssuePhoto', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Fecha y hora de creación
    updated_at = models.DateTimeField(auto_now=True)      # Fecha y hora de la última actualización

    def get_created_at_local(self):
            """
            Devuelve la fecha y hora de `created_at` convertida a la zona horaria local.
            """
            return timezone.localtime(self.created_at)
    def get_updated_at_local(self):
            """
            Devuelve la fecha y hora de `created_at` convertida a la zona horaria local.
            """
            return timezone.localtime(self.update_at)
       
    
    def __str__(self):
        return f"Albarán {self.fiscal_year}/{self.delivery_number} - Cliente {self.customer.client_number if self.customer else 'Sin cliente'}"

class DeliveryImage(models.Model):
    image = models.ImageField(upload_to=get_delivery_image_upload_to)

class IssuePhoto(models.Model):
    image = models.ImageField(upload_to=get_issue_photo_upload_to)
    

class Customer(models.Model):
    client_number = models.PositiveIntegerField(unique=True)  # Número de cliente
    name = models.CharField(max_length=255)  # Nombre del cliente
    email = models.EmailField()  # Correo electrónico del cliente

    def __str__(self):
        return f"{self.name} - {self.client_number}"
    
class EmailNotificationFailure(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)  # Cliente relacionado con el fallo
    reason = models.TextField()  # Descripción del error o razón del fallo
    timestamp = models.DateTimeField(auto_now_add=True)  # Fecha y hora del fallo

    def __str__(self):
        return f"Fallo de Email - Cliente: {self.customer} - Fecha: {self.timestamp}"

class Product(models.Model):
    product_number = models.PositiveIntegerField(unique=True)  # Número de producto
    description = models.CharField(max_length=255)  # Descripción del producto
    supplier_number = models.PositiveIntegerField()  # Número de proveedor
    supplier_name = models.CharField(max_length=255)  # Nombre del proveedor

    def __str__(self):
        return f"{self.product_number} - {self.description}"