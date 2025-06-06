import os
from django.db import models
from django.core.files.storage import default_storage
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

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
    return upload_to(instance, filename, f"deliveries/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}")

def get_issue_photo_upload_to(instance, filename):
    return upload_to(instance, filename, f"issues/{instance.delivery.fiscal_year}_{instance.delivery.delivery_number}")

class DeliveryImage(models.Model):
    delivery = models.ForeignKey(
        'Delivery', 
        related_name='delivery_image_set',  # Ajustar el related_name para evitar conflictos
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to=get_delivery_image_upload_to)

    def __str__(self):
        return self.image.name
  

class IssuePhoto(models.Model):
    delivery = models.ForeignKey(
        'Delivery', 
        related_name='issue_photo_set',  # Ajustar el related_name para evitar conflictos
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to=get_issue_photo_upload_to)

    def __str__(self):
        return self.image.name
   
    

class Delivery(models.Model):
    VISIT_TYPE_CHOICES = [
        ('delivery', 'Entrega'),
        ('verification', 'Verificación'),
        ('resolution', 'Resolución'),
    ]
    
    STATUS_CHOICES = [
        ('pendiente_tratar', 'Pendiente de Tratar'),
        ('tratado_pendiente_resolucion', 'Tratado Pendiente de Resolución'),
        ('finalizado', 'Finalizado'),
        ('no_resuelto', 'No Resuelto'),
        
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
    delivery_images = models.ManyToManyField(DeliveryImage, related_name='deliveries', blank=True)
    issue_photos = models.ManyToManyField(IssuePhoto, related_name='deliveries', blank=True)
    created_at = models.DateTimeField(default=timezone.now)  # Fecha y hora de creación
    updated_at = models.DateTimeField(auto_now=True)      # Fecha y hora de la última actualización
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pendiente de tratar')
    incident_number = models.CharField(max_length=50, blank=True, null=True)  # Nuevo campo
    status_satisfaction = models.CharField(max_length=50, choices=[
        ('no_tratado', 'No Tratado'),
        ('tratado', 'Tratado')
    ], default='no_tratado')  # Nuevo campo para gestionar la satisfacción del cliente


    def save(self, *args, **kwargs):
        if self.status != 'tratado_pendiente_resolucion':  # Solo ajustar si no está en el estado deseado
            if self.visit_type == 'delivery':
                if self.has_issue:
                    self.status = 'pendiente_tratar'
                else:
                    self.status = 'finalizado'
            elif self.visit_type in ['verification', 'resolution']:
                if self.is_resolved:
                    self.status = 'finalizado'
                else:
                    self.status = 'no_resuelto'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Albarán {self.fiscal_year}/{self.delivery_number} - Cliente {self.customer.client_number if self.customer else 'Sin cliente'}"

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



class Customer(models.Model):
    client_number = models.PositiveIntegerField(unique=True)  # Número de cliente
    name = models.CharField(max_length=255)  # Nombre del cliente
    email = models.EmailField()  # Correo electrónico del cliente

    def __str__(self):
        return f"{self.name} - {self.client_number}"
    
class EmailNotificationFailure(models.Model):
    
    EMAIL_TYPE_CHOICES = [
        ('albaran_incidencia', 'Albarán con Incidencia'),
        ('registro_incidencia', 'Registro de Incidencia'),
        ('resolucion_incidencia', 'Resolución de Incidencia'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)  # Cliente relacionado con el fallo
    reason = models.TextField()  # Descripción del error o razón del fallo
    timestamp = models.DateTimeField(auto_now_add=True)  # Fecha y hora del fallo
    albaran = models.CharField(max_length=20, blank=True, null=True)  # Almacena el albarán con el formato "año_fiscal/nºdealbaran"
    email_type = models.CharField(max_length=50, choices=EMAIL_TYPE_CHOICES, blank=True, null=True)  # Tipo de email que falló
    status = models.CharField(max_length=20, default='pendiente_contacto')  # Asegúrate de que el campo status esté definido    
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, null=True, blank=True)
    def __str__(self):
        return f"Fallo de Email - Cliente: {self.customer} - Albarán: {self.albaran} - Tipo: {self.email_type} - Fecha: {self.timestamp}"

class Product(models.Model):
    product_number = models.PositiveIntegerField(unique=True)  # Número de producto
    description = models.CharField(max_length=255)  # Descripción del producto
    supplier_number = models.PositiveIntegerField()  # Número de proveedor
    supplier_name = models.CharField(max_length=255)  # Nombre del proveedor

    def __str__(self):
        return f"{self.product_number} - {self.description}"