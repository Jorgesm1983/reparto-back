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
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta

import json

# from .models import Delivery

import os

@login_required
def admin_page_view(request):
    # Lógica para la página del administrador
    return render(request, 'admin_page.html')

@csrf_exempt
def login_view(request):
    if request.method == 'POST':

        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Obtener o crear el token para el usuario
                token, _ = Token.objects.get_or_create(user=user)
                
                # Devolver el token en la respuesta
                return JsonResponse({'message': 'Login exitoso', 'token': token.key})
            else:
                return JsonResponse({'message': 'Credenciales incorrectas'}, status=401)
        except json.JSONDecodeError:
            return JsonResponse({'message': 'Error al decodificar JSON'}, status=400)
    return JsonResponse({'message': 'Método no permitido'}, status=405)

def logout_view(request):
    logout(request)
    return JsonResponse({'message': 'Logout exitoso'})

class DeliveryCreateView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer

    def post(self, request, *args, **kwargs):
        client_number = request.data.get('client_number')
        customer = Customer.objects.filter(client_number=client_number).first()
        
        data = request.data.copy()
        data['customer'] = customer.id if customer else None

        has_issue = data.get('has_issue', 'false').lower() == 'true'
        data['has_issue'] = has_issue

        # Determinar el estado según si tiene problemas
        data['status'] = 'pendiente de tratar' if has_issue else 'finalizado'
        
        issues = request.data.getlist('issues', [])

        serializer = DeliverySerializer(data=data)
        if serializer.is_valid():
            delivery = serializer.save(user=request.user, customer=customer)
            
            serializer = DeliverySerializer(delivery, context={'request': request})

            # Enviar email si hay una incidencia
            if delivery.has_issue:
                try:
                    issues = delivery.issues or []
                    print(f"Issues extraídos desde la base de datos: {issues}")
                    self._send_issue_email(delivery, issues)
                except Exception as e:
                    # Registrar error de envío de email
                    EmailNotificationFailure.objects.create(
                        customer=delivery.customer,
                        reason=str(e)
                    )
                    print(f"Error enviando el correo: {e}")

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _send_issue_email(self, delivery, issues):
        try:
            product_details = []
            for issue in issues:
                product = Product.objects.filter(product_number=issue).first()
                if product:
                    product_details.append(f"<li>E-{product.product_number} {product.description}</li>")
                else:
                    print(f"No se encontró un producto con el número: {issue}")
            # Inicializar productos_afectados como una cadena vacía antes del bloque condicional.
            productos_afectados = ""

            # Generar el cuerpo del correo con los productos afectados como una lista HTML
            productos_afectados = "".join(product_details) if product_details else "<li>Sin detalles de productos.</li>"

            # Comprobar si el cliente tiene un email
            if not delivery.customer or not delivery.customer.email:
                raise ValueError("Correo no proporcionado")

            # Enviar el correo de notificación
            send_mail(
                subject=f"Incidencia registrada - Albarán N.º {delivery.fiscal_year}/{delivery.delivery_number}",
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
        
@api_view(['GET'])
def recent_deliveries(request):
    """
    Listar albaranes de los últimos 7 días con filtros y resaltar aquellos con incidencias o no resueltos.
    """
    today = timezone.now()
    seven_days_ago = today - timedelta(days=7)
    deliveries = Delivery.objects.filter(created_at__gte=seven_days_ago).order_by('-created_at')

    
    # Aplicar filtros desde los parámetros de la URL si es necesario
    if 'visit_type' in request.GET:
        deliveries = deliveries.filter(visit_type=request.GET['visit_type'])
    if 'status' in request.GET:
        deliveries = deliveries.filter(status=request.GET['status'])
    if 'has_issue' in request.GET:
        deliveries = deliveries.filter(has_issue=request.GET['has_issue'])

    serializer = DeliverySerializer(deliveries, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def update_incident(request, delivery_id):
    """
    Actualizar el número de incidencia de un albarán y cambiar su estado.
    Enviar un correo electrónico al cliente.
    """
    try:
        delivery = Delivery.objects.get(id=delivery_id)
        incident_number = request.data.get('incident_number')

        if not incident_number:
            return Response({'error': 'Número de incidencia requerido'}, status=400)

        # Actualizar el número de incidencia y el estado
        delivery.incident_number = incident_number
        delivery.status = 'tratado pendiente de resolución'
        delivery.save()

        # Enviar correo electrónico al cliente
        send_mail(
            subject=f'Incidencia registrada: {incident_number}',
            message=f'Estimado cliente, se ha registrado una incidencia con el número {incident_number}.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[delivery.customer.email],
        )

        return Response({'message': 'Número de incidencia actualizado y correo enviado correctamente.'})
    except Delivery.DoesNotExist:
        return Response({'error': 'Albarán no encontrado'}, status=404)
    
@api_view(['GET'])
def calculate_response_time(request, delivery_id):
    try:
        delivery = Delivery.objects.get(id=delivery_id)
        time_difference = delivery.updated_at - delivery.created_at
        return Response({'response_time': str(time_difference)})
    except Delivery.DoesNotExist:
        return Response({'error': 'Albarán no encontrado'}, status=404)
    
@api_view(['GET'])
def recent_deliveries(request):
    """
    Listar albaranes de los últimos 7 días con filtros y resaltar aquellos con incidencias o no resueltos.
    """
    today = timezone.now()
    seven_days_ago = today - timedelta(days=7)
    deliveries = Delivery.objects.filter(created_at__gte=seven_days_ago)

    # Aplicar filtros desde los parámetros de la URL si es necesario
    if 'visit_type' in request.GET:
        deliveries = deliveries.filter(visit_type=request.GET['visit_type'])
    if 'status' in request.GET:
        deliveries = deliveries.filter(status=request.GET['status'])
    if 'has_issue' in request.GET:
        deliveries = deliveries.filter(has_issue=request.GET['has_issue'])

    serializer = DeliverySerializer(deliveries, many=True, context={'request': request})
    return Response(serializer.data)