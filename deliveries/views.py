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
            return Response({"error": f"No se encontró ningún cliente con el número {client_number}"}, status=status.HTTP_400_BAD_REQUEST)

        if request.data.get('visit_type') in ['verification', 'resolution']:
            request.data.pop('issues', None)
        
        serializer = DeliverySerializer(data=request.data)
        if serializer.is_valid():
            delivery = serializer.save(user=request.user, customer=customer)  # Asociar el usuario autenticado
# Enviar email si hay incidencia
            if delivery.has_issue:
                try:
                    # Comprobar si el cliente tiene un email
                    if not delivery.customer or not delivery.customer.email:
                        raise ValueError("Correo no proporcionado")

                    # Enviar el correo de notificación
                    send_mail(
                        subject=f"Incidencia registrada - Albarán N.º {delivery.delivery_number}",
                            message=f"Estimado/a {delivery.customer.name},\n\n"
                                    f"Le informamos que se ha registrado una incidencia en su albarán con los siguientes detalles:\n\n"
                                    f"- Número de Albarán: {delivery.delivery_number}\n"
                                    f"- Año Fiscal: {delivery.fiscal_year}\n"
                                    f"- Número de Cliente: {delivery.client_number}\n\n"
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