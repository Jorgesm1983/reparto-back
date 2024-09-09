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
    return os.path.join(folder_name, new_filename)

def get_delivery_image_upload_to(instance, filename):
    """Genera la ruta de almacenamiento para las imágenes de entrega."""
    return upload_to(instance, filename, f'deliveries/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}')

def get_issue_photo_upload_to(instance, filename):
    """Genera la ruta de almacenamiento para las fotos de incidencias."""
    return upload_to(instance, filename, f'issues/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}')

class Delivery(models.Model):
    fiscal_year = models.CharField(max_length=4)
    delivery_number = models.PositiveIntegerField()
    client_conformity = models.BooleanField(default=True)
    has_issue = models.BooleanField(default=False)
    observations = models.TextField(blank=True, null=True)
    issues = models.JSONField(default=list)
    delivery_images = models.ManyToManyField('DeliveryImage', blank=True)
    issue_photos = models.ManyToManyField('IssuePhoto', blank=True)
    
    def __str__(self):
        return f"Albarán {self.fiscal_year}/{self.delivery_number}"

class DeliveryImage(models.Model):
    image = models.ImageField(upload_to=get_delivery_image_upload_to)

class IssuePhoto(models.Model):
    image = models.ImageField(upload_to=get_issue_photo_upload_to)