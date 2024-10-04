from rest_framework import viewsets
from rest_framework import status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Delivery, DeliveryImage, IssuePhoto, Customer, EmailNotificationFailure, Product
from .serializers import DeliverySerializer
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from .models import EmailNotificationFailure
from django.conf import settings


# from .models import Delivery

import os
    
class DeliveryCreateView(APIView):
    permission_classes = [IsAuthenticated]  # Requiere autenticación
    
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    
    def post(self, request, *args, **kwargs):
        client_number = request.data.get('client_number')
         # Buscar el cliente por número de cliente
        customer = Customer.objects.filter(client_number=client_number).first()

        if not customer:
            # No devolver error, permitir que se guarde sin cliente
            customer = None  # Si no se encuentra, el cliente será None
            
        issues = request.data.getlist('issues', [])  # Obtener los números de productos con incidencia

        
        if request.data.get('visit_type') in ['verification', 'resolution']:
            request.data.pop('issues', None)
        
        serializer = DeliverySerializer(data=request.data)
        if serializer.is_valid():
            delivery = serializer.save(user=request.user, customer=customer)  # Asociar el usuario autenticado
# Enviar email si hay incidencia
            if delivery.has_issue and issues:
                try:
                    # Obtener los detalles de los productos afectados
                    product_details = []
                    for issue in issues:
                        product = Product.objects.filter(product_number=issue).first()
                        if product:
                            product_details.append(f"<li>E-{product.product_number} {product.description}</li>")

                    # Generar el cuerpo del correo con los productos afectados como una lista HTML
                    if product_details:  # Asegurar que hay productos para incluir en el correo
                        productos_afectados = "".join(product_details)  # Formatear como lista HTML
                    
                    # Comprobar si el cliente tiene un email
                    if not delivery.customer or not delivery.customer.email:
                        raise ValueError("Correo no proporcionado")

                    # Enviar el correo de notificación
                    send_mail(
                        subject=f"Incidencia registrada - Albarán N.º {delivery.delivery_number}",
                            message=f"Estimado/a {delivery.customer.name},\n\n"
                                f"Le informamos que se ha registrado una incidencia en su albarán con los siguientes detalles:\n\n"
                                f"- Número de Albarán: {delivery.fiscal_year}/{delivery.delivery_number}\n"
                                f"- Número de Cliente: {delivery.client_number}\n\n"
                                f"Productos Afectados:\n{productos_afectados}\n\n"
                                f"Nuestro equipo ha tomado nota de esta incidencia y está trabajando para resolverla a la mayor brevedad posible. "
                                f"Nos pondremos en contacto con usted en cuanto tengamos más información o necesitemos alguna colaboración de su parte.\n\n"
                                f"Agradecemos su paciencia y lamentamos cualquier inconveniente que esta situación pueda ocasionarle. "
                                f"Si tiene alguna duda o consulta adicional, no dude en ponerse en contacto con nosotros.\n\n"
                                f"Atentamente,\n"
                                f"[Nombre de la Empresa]\n"
                                f"Departamento de Atención al Cliente\n"
                                f"[Teléfono de contacto]\n"
                                f"[Correo electrónico de contacto]",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[delivery.customer.email],
                        fail_silently=False,
                        html_message=f"""
                            <p>Estimado/a {delivery.customer.name},</p>
                            <p>Le informamos que se ha registrado una incidencia en su albarán con los siguientes detalles:</p>
                            <ul>
                                <li><strong>Número de Albarán:</strong> {delivery.fiscal_year}/{delivery.delivery_number}</li>
                                <li><strong>Número de Cliente:</strong> {delivery.client_number}</li>
                            </ul>
                            <p><strong>Productos Afectados:</strong></p>
                            <ul>
                                {productos_afectados}
                            </ul>
                            <p>Nuestro equipo ha tomado nota de esta incidencia y está trabajando para resolverla a la mayor brevedad posible.</p>
                            <p>Nos pondremos en contacto con usted en cuanto tengamos más información o necesitemos alguna colaboración de su parte.</p>
                            <p>Agradecemos su paciencia y lamentamos cualquier inconveniente que esta situación pueda ocasionarle.</p>
                            <p>Si tiene alguna duda o consulta adicional, no dude en ponerse en contacto con nosotros.</p>
                            <p>Atentamente,</p>
                            <p>WOW Málaga<br>
                            Departamento de Atención al Cliente<br>
                            952 91 61 18<br>
                            bahiaazul@mubak.com</p>

                            <hr>

                            <p>Dear {delivery.customer.name},</p>
                            <p>We inform you that an issue has been registered with your delivery with the following details:</p>
                            <ul>
                                <li><strong>Delivery Number:</strong> {delivery.fiscal_year}/{delivery.delivery_number}</li>
                                <li><strong>Customer Number:</strong> {delivery.client_number}</li>
                            </ul>
                            <p><strong>Affected Products:</strong></p>
                            <ul>
                                {productos_afectados}
                            </ul>
                            <p>Our team has taken note of this issue and is working to resolve it as soon as possible.</p>
                            <p>We will contact you as soon as we have more information or require your assistance.</p>
                            <p>We appreciate your patience and apologize for any inconvenience this situation may cause you.</p>
                            <p>If you have any questions or additional concerns, please feel free to contact us.</p>
                            <p>Sincerely,</p>
                            <p>WOW Málaga<br>
                            Customer Service Department<br>
                            952 91 61 18<br>
                            bahiaazul@mubak.com</p>
                        """
                    )
                    
                    print(f"Correo enviado a {delivery.customer.email}")
                    
                except Exception as e:
                    # Registrar el fallo del correo en la base de datos
                    EmailNotificationFailure.objects.create(
                        customer=delivery.customer,
                        reason=str(e)
                    )
                    print(f"Error enviando el correo: {e}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # En caso de errores en la validación, devolver los errores
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_view(['POST'])
    def register(request):
        username = request.data.get('username')
        password = request.data.get('password')

        if User.objects.filter(username=username).exists():
            return Response({"error": "El usuario ya existe."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password)
        token = Token.objects.create(user=user)

        return Response({"token": token.key}, status=status.HTTP_201_CREATED)

class ProductDetailView(APIView):
    
    def get(self, request, product_id):
        try:
            product = Product.objects.get(product_number=product_id)
            return Response({
                'id': product.product_number,
                'description': product.description,
            }, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
class CustomerDetailView(APIView):
    def get(self, request, client_number):
        try:
            customer = Customer.objects.get(client_number=client_number)  # Buscar cliente por número
            return Response({
                'client_number': customer.client_number,
                'name': customer.name,
            }, status=status.HTTP_200_OK)
        except Customer.DoesNotExist:
            return Response({'error': 'Cliente no encontrado'}, status=status.HTTP_404_NOT_FOUND)