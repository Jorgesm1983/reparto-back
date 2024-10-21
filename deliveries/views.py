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
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail, BadHeaderError
from .models import EmailNotificationFailure
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta, datetime
from django.db import transaction
from django.http import QueryDict
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny
from smtplib import SMTPException
from django.core.exceptions import ValidationError
from django.core.validators import validate_email# <-- Añade esta línea
from django.shortcuts import get_object_or_404


import json

# from .models import Delivery

import os

@login_required
def admin_page_view(request):
    # Lógica para la página del administrador
    return render(request, 'admin_page.html')

@csrf_exempt
def check_session(request):
    if request.user.is_authenticated:
        return JsonResponse({'status': 'authenticated'}, status=200)
    else:
        return JsonResponse({'status': 'unauthenticated'}, status=401)

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
                
                 # Establecer la expiración de la sesión a 12 horas (43200 segundos)
                request.session.set_expiry(60 * 60 * 6)  # 12 horas
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
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        client_number = request.data.get('client_number')
        customer = Customer.objects.filter(client_number=client_number).first()
        
        if request.FILES:  # Comprobar si hay archivos en la solicitud
            data = request.data.copy()
            files = request.FILES
        else:
            data = request.data.copy()
        data['customer'] = customer.id if customer else None
        
        visit_type = data.get('visit_type')
        
        has_issue = data.get('has_issue', 'false').lower() == 'true'
        data['has_issue'] = has_issue
        
        is_resolved = data.get('is_resolved', 'false').lower() == 'true'
        data['is_resolved'] = is_resolved
        
        # Determinar el estado según si tiene problemas
        if visit_type == 'resolution' or visit_type == 'verification':
        # Albaranes de verificación o resolución solo tienen dos estados: finalizado o no resuelto
            if is_resolved:
                data['status'] = 'finalizado'
            else:
                data['status'] = 'no_resuelto'  # Podría ser otro nombre como 'pendiente_resolucion'
        else:
            # Albaranes de entrega tienen lógica más compleja basada en incidencias
            if has_issue:
                data['status'] = 'pendiente_tratar'
            else:
                data['status'] = 'finalizado'
        
        issues = request.data.getlist('issues', [])
        print(f"Issues desde el request: {issues}")  # Log para verificar las incidencias
        
        serializer = DeliverySerializer(data=data)
        
         # Añadir depuración para ver exactamente qué errores está devolviendo el serializer
        if not serializer.is_valid():
            print(f"Errores del serializer: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if serializer.is_valid():
            delivery = serializer.save(user=request.user, customer=customer)
            
            print(f"Delivery guardado: ID={delivery.id}, Estado={delivery.status}, Conformidad Cliente={delivery.client_conformity}")
            
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
                    
            if visit_type in ['verification', 'resolution'] and delivery.is_resolved:
                try:
                    # Actualizar los albaranes de entrega anteriores a finalizado
                    Delivery.objects.filter(
                        customer=delivery.customer,
                        visit_type='delivery',
                        status='tratado_pendiente_resolucion'
                    ).update(status='finalizado')
                    print(f"Albaranes de entrega anteriores actualizados a 'finalizado' para el cliente {delivery.customer.client_number}")
                
                    # Actualizar los albaranes de verificación anteriores a finalizado
                    Delivery.objects.filter(
                        customer=delivery.customer,
                        visit_type='verification',
                        status='no_resuelto'  # Cambiar de no resuelto a finalizado si la resolución se da
                    ).update(status='finalizado')
                    print(f"Albaranes de verificación anteriores actualizados a 'finalizado' para el cliente {delivery.customer.client_number}")
                
                    # Actualizar los albaranes de resolución anteriores a finalizado
                    Delivery.objects.filter(
                        customer=delivery.customer,
                        visit_type='resolution',
                        status='no_resuelto'  # Cambiar de no resuelto a finalizado si la resolución se da
                    ).update(status='finalizado')
                    print(f"Albaranes de resolución no resueltos actualizados a 'finalizado' para el cliente {delivery.customer.client_number}")
                    
                except Exception as e:
                    print(f"Error al actualizar los albaranes anteriores: {e}")
                    
                    # Enviar email si la incidencia está resuelta
            if delivery.is_resolved:
                try:
                    self._send_resolution_email(delivery)
                except Exception as e:
                    # Registrar error de envío de email de resolución
                    EmailNotificationFailure.objects.create(
                        customer=delivery.customer,
                        reason=str(e)
                    )
                    print(f"Error enviando el correo de resolución: {e}")

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

            productos_afectados = "".join(product_details) if product_details else "<li>Sin detalles de productos.</li>"

            # Comprobar si el cliente tiene un email
            if not delivery.customer or not delivery.customer.email:
                raise ValueError("Cliente sin email registrado")

            # Validar el formato del email
            validate_email(delivery.customer.email)

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
                    <a href="tel:+34952916118">+34 952 91 61 18</a><br>
                    <a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>

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
                    <a href="tel:+34952916118">+34 952 91 61 18</a><br>
                    <a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>
                """
            )
            print(f"Correo enviado a {delivery.customer.email}")

        except ValidationError:
            # Email con formato incorrecto
            albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
            EmailNotificationFailure.objects.create(
                customer=delivery.customer,
                reason="Formato de email incorrecto",
                albaran=albaran_info,
                email_type='albaran_incidencia',
                delivery=delivery  # Asegúrate de asociar la entrega
            )
            print(f"Error: Formato de email incorrecto para {delivery.customer.email}")

        except BadHeaderError:
            # Error en los encabezados del correo
            albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
            EmailNotificationFailure.objects.create(
                customer=delivery.customer,
                reason="Encabezados de correo inválidos",
                albaran=albaran_info,
                email_type='albaran_incidencia',
                delivery=delivery  # Asegúrate de asociar la entrega
            )
            print(f"Error: Encabezados inválidos para {delivery.customer.email}")

        except SMTPException as e:
            # Error de SMTP (correo no válido, no existe, etc.)
            albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
            EmailNotificationFailure.objects.create(
                customer=delivery.customer,
                reason=str(e),
                albaran=albaran_info,
                email_type='albaran_incidencia',
                delivery=delivery  # Asegúrate de asociar la entrega
            )
            print(f"Error SMTP enviando el correo a {delivery.customer.email}: {e}")

        except Exception as e:
            # Otro error imprevisto
            albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
            EmailNotificationFailure.objects.create(
                customer=delivery.customer,
                reason=str(e),
                albaran=albaran_info,
                email_type='albaran_incidencia',
                delivery=delivery  # Asegúrate de asociar la entrega
            )
            print(f"Error desconocido enviando el correo a {delivery.customer.email}: {e}")


    def _send_resolution_email(self, delivery):
        if delivery.is_resolved:
            try:
                validate_email(delivery.customer.email)
                # Enviar correo de resolución
                send_mail(
                    subject=f"Incidencia resuelta - Albarán N.º {delivery.fiscal_year}/{delivery.delivery_number}",
                    message=f"""
                    Estimado/a {delivery.customer.name},

                    Le informamos que su incidencia ha sido solucionada con éxito.

                    Nuestro equipo ha solucionado el problema y agradecemos su paciencia durante el proceso.

                    Si tiene alguna duda o consulta adicional, no dude en ponerse en contacto con nosotros.

                    Atentamente,
                    WOW Málaga
                    Departamento de Atención al Cliente
                    952 91 61 18
                    bahiaazul@mubak.com
                    """,
                    html_message=f"""
                    <p>Estimado/a {delivery.customer.name},</p>
                    <p>Le informamos que su incidencia ha sido solucionada con éxito.</p>
                    <p>Nuestro equipo ha solucionado el problema y agradecemos su paciencia durante el proceso.</p>
                    <p>Si tiene alguna duda o consulta adicional, no dude en ponerse en contacto con nosotros.</p>
                    <p>Atentamente,</p>
                    <p>WOW Málaga<br>
                    Departamento de Atención al Cliente<br>
                    <a href="tel:+34952916118">+34 952 91 61 18</a><br>
                    <a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>
                    
                    <hr>

                    <p>Dear {customer.name},</p>
                    <p>Your issue has been successfully resolved for delivery {delivery.fiscal_year}/{delivery.delivery_number}.</p>
                    <p>If you have any questions, please feel free to contact us.</p>
                    <p>Sincerely,</p>
                    <p>WOW Málaga<br>Customer Service Department<br><a href="tel:+34952916118">+34 952 91 61 18</a><br><a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[delivery.customer.email],
                    fail_silently=False,
                )
                print(f"Correo enviado a {delivery.customer.email} sobre la resolución de la incidencia.")

            except ValidationError:
                # Email con formato incorrecto
                albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
                EmailNotificationFailure.objects.create(
                    customer=delivery.customer,
                    reason="Formato de email incorrecto",
                    albaran=albaran_info,
                    email_type='resolucion_incidencia',
                    delivery=delivery  # Asegúrate de asociar la entrega
                )
                print(f"Error: Formato de email incorrecto para {delivery.customer.email}")

            except BadHeaderError:
                # Error en los encabezados del correo
                albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
                EmailNotificationFailure.objects.create(
                    customer=delivery.customer,
                    reason="Encabezados de correo inválidos",
                    albaran=albaran_info,
                    email_type='resolucion_incidencia',
                    delivery=delivery  # Asegúrate de asociar la entrega
                )
                print(f"Error: Encabezados inválidos para {delivery.customer.email}")

            except SMTPException as e:
                # Error de SMTP (correo no válido, no existe, etc.)
                albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
                EmailNotificationFailure.objects.create(
                    customer=delivery.customer,
                    reason=str(e),
                    albaran=albaran_info,
                    email_type='resolucion_incidencia',
                    delivery=delivery  # Asegúrate de asociar la entrega
                )
                print(f"Error SMTP enviando el correo a {delivery.customer.email}: {e}")

            except Exception as e:
                # Otro error imprevisto
                albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
                EmailNotificationFailure.objects.create(
                    customer=delivery.customer,
                    reason=str(e),
                    albaran=albaran_info,
                    email_type='resolucion_incidencia',
                    delivery=delivery  # Asegúrate de asociar la entrega
                )
                print(f"Error desconocido enviando el correo a {delivery.customer.email}: {e}")
                
        else:
            # Si no tiene email registrado
            albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
            EmailNotificationFailure.objects.create(
                customer=delivery.customer,
                reason="Cliente sin email registrado",
                albaran=albaran_info,
                email_type='registro_incidencia',
                delivery=delivery  # Asegúrate de asociar la entrega
            )
            print(f"Error: Cliente sin email registrado")


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
        

@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
        delivery.status = 'tratado_pendiente_resolucion'  # Usar el valor exacto de STATUS_CHOICES
        delivery.save()

        # Verificar si el cliente tiene un email registrado
        if delivery.customer.email:
            try:
                # Validar si el formato del email es correcto
                validate_email(delivery.customer.email)

                # Intentar enviar el correo
                send_mail(
                    subject=f'Incidencia registrada: {incident_number}',
                    message=(
                        f'Estimado/a {delivery.customer.name},\n\n'
                        f'Se ha registrado una incidencia con el número {incident_number} para su albarán '
                        f'{delivery.fiscal_year}/{delivery.delivery_number}. Nuestro equipo está trabajando para '
                        f'resolverla a la mayor brevedad posible.\n\n'
                        f'Agradecemos su paciencia.\n\n'
                        f'Atentamente,\n'
                        f'WOW Málaga\n'
                        f'Departamento de Atención al Cliente\n'
                        f'952 91 61 18\n'
                        f'bahiaazul@mubak.com'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[delivery.customer.email],
                    fail_silently=False,
                    html_message=f"""
                        <p>Estimado/a {delivery.customer.name},</p>
                            <p>Se ha registrado una incidencia con el número {incident_number} para su albarán {delivery.fiscal_year}/{delivery.delivery_number}. Nuestro equipo está trabajando para resolverla a la mayor brevedad posible.</p>
                            <p>Agradecemos su paciencia.</p>
                            <p>Atentamente,</p>
                            <p>WOW Málaga<br>
                            Departamento de Atención al Cliente<br>
                            <a href="tel:+34952916118">952 91 61 18</a><br>
                            <a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>

                            <hr>

                            <p>Dear {delivery.customer.name},</p>
                            <p>An issue has been registered with incident number {incident_number} for your delivery {delivery.fiscal_year}/{delivery.delivery_number}. Our team is working to resolve it as soon as possible.</p>
                            <p>Thank you for your patience.</p>
                            <p>Sincerely,</p>
                            <p>WOW Málaga<br>
                            Customer Service Department<br>
                            <a href="tel:+34952916118">+34 952 91 61 18</a><br>
                            <a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>

                        """
                )
                print(f"Correo enviado a {delivery.customer.email}")

            except ValidationError:
                # Email con formato incorrecto
                albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
                EmailNotificationFailure.objects.create(
                    customer=delivery.customer,
                    reason="Formato de email incorrecto",
                    albaran=albaran_info,
                    email_type='registro_incidencia',
                    delivery=delivery  # Asegúrate de asociar la entrega
                )
                print(f"Error: Formato de email incorrecto para {delivery.customer.email}")

            except BadHeaderError:
                # Error en los encabezados del correo
                albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
                EmailNotificationFailure.objects.create(
                    customer=delivery.customer,
                    reason="Encabezados de correo inválidos",
                    albaran=albaran_info,
                    email_type='registro_incidencia',
                    delivery=delivery  # Asegúrate de asociar la entrega
                )
                print(f"Error: Encabezados inválidos para {delivery.customer.email}")

            except SMTPException as e:
                # Error de SMTP (correo no válido, no existe, etc.)
                albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
                EmailNotificationFailure.objects.create(
                    customer=delivery.customer,
                    reason=str(e),
                    albaran=albaran_info,
                    email_type='registro_incidencia',
                    delivery=delivery  # Asegúrate de asociar la entrega
                )
                print(f"Error SMTP enviando el correo a {delivery.customer.email}: {e}")

            except Exception as e:
                # Otro error imprevisto
                albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
                EmailNotificationFailure.objects.create(
                    customer=delivery.customer,
                    reason=str(e),
                    albaran=albaran_info,
                    email_type='registro_incidencia',
                    delivery=delivery  # Asegúrate de asociar la entrega
                )
                print(f"Error desconocido enviando el correo a {delivery.customer.email}: {e}")

        else:
            # Si no tiene email registrado
            albaran_info = f"{delivery.fiscal_year}/{delivery.delivery_number}"
            EmailNotificationFailure.objects.create(
                customer=delivery.customer,
                reason="Cliente sin email registrado",
                albaran=albaran_info,
                email_type='registro_incidencia',
                delivery=delivery  # Asegúrate de asociar la entrega
            )
            print(f"Error: Cliente sin email registrado")

        return Response({
            'message': 'Número de incidencia actualizado y correo enviado correctamente (si procede).',
            'new_status': delivery.status,
        })
    except Delivery.DoesNotExist:
        return Response({'error': 'Albarán no encontrado'}, status=404)
    except Exception as e:
        print(f"Error interno: {str(e)}")
        return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
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
    Listar albaranes con filtros opcionales y resaltar aquellos con incidencias o no resueltos.
    """
    today = timezone.now()
    deliveries = Delivery.objects.all()  # Puedes cambiarlo según la lógica de tu negocio

    # Filtrar por rango de fechas si se proporcionan
    date_from = request.GET.get('dateFrom', None)
    date_to = request.GET.get('dateTo', None)
    
    print(f"dateFrom: {date_from}, dateTo: {date_to}")  # Verificar los valores de las fechas
    
    try:
        if date_from:
            date_from = datetime.strptime(date_from, "%Y-%m-%d")
            deliveries = deliveries.filter(created_at__gte=date_from)
            
        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1) - timedelta(microseconds=1)
            deliveries = deliveries.filter(created_at__lte=date_to)
            
    except ValueError as e:
        # Si hay error en la conversión de fecha, enviar error con 400 Bad Request
        return Response({'error': f'Formato de fecha inválido: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Si no se pasa ningún filtro de fecha, se muestran los últimos 7 días
    if not date_from and not date_to:
       
        seven_days_ago = today - timedelta(days=7)
        deliveries = Delivery.objects.filter(created_at__gte=seven_days_ago)
    

    # Filtros adicionales desde el front-end
    
    visit_type = request.GET.get('visit_type', None)
    delivery_status = request.GET.get('delivery_status', None)
    has_issue = request.GET.get('has_issue', None)


    # Aplicar otros filtros si están presentes
    if visit_type:
        deliveries = deliveries.filter(visit_type=visit_type)
    if delivery_status:
        deliveries = deliveries.filter(status=status)
    if has_issue:
        deliveries = deliveries.filter(has_issue=has_issue)

    if deliveries.exists():
        serializer = DeliverySerializer(deliveries, many=True, context={'request': request})
        return Response(serializer.data)
    else:
        return Response([], status=status.HTTP_200_OK)  # Devuelve una lista vacía si no hay registros
    
    # Albaranes pendientes de tratar
def albaranes_pendientes(request):
    count = Delivery.objects.filter(status='pendiente_tratar').count()
    return JsonResponse({'count': count})

# Albaranes tratados pendientes de resolución
def albaranes_tratados(request):
    count = Delivery.objects.filter(status='tratado_pendiente_resolucion').count()
    return JsonResponse({'count': count})

# Albaranes sin resolver
def albaranes_no_resueltos(request):
    count = Delivery.objects.filter(status='no_resuelto').count()
    return JsonResponse({'count': count})

@api_view(['GET'])  # Permitir acceso público
@permission_classes([AllowAny])
def email_failures(request):
    """
    Listar los fallos de email, incluyendo información de cliente y albarán.
    """
    try:
        # Obtener parámetros de filtro
        date_from = request.GET.get('dateFrom', None)
        date_to = request.GET.get('dateTo', None)
        email_type = request.GET.get('email_type', None)
        client_number = request.GET.get('client_number', None)
        status = request.GET.get('status', None)
        reason = request.GET.get('reason', None)
        # Base query para obtener todos los fallos de emails
        failures = EmailNotificationFailure.objects.select_related('customer').all()

        # Aplicar filtros
        if date_from:
            failures = failures.filter(timestamp__gte=datetime.strptime(date_from, "%Y-%m-%d"))
        if date_to:
            failures = failures.filter(timestamp__lte=datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1))
        if email_type:
            failures = failures.filter(email_type=email_type)
        if client_number:
            failures = failures.filter(customer__client_number=client_number)
        if status:
            failures = failures.filter(status=status)
        if reason:
            failures = failures.filter(reason=reason)
            
        failures = failures.order_by('-timestamp')  # Orden descendente por fecha de creación

        result = []

        for failure in failures:
            result.append({
                'id': failure.id, 
                'reason': failure.reason,
                'customer_email': failure.customer.email if failure.customer else None,
                'albaran': failure.albaran,
                'email_type': failure.email_type,
                'status': failure.status,  # Incluimos el estado del fallo
                'created_at': failure.timestamp.strftime('%d/%m/%y %H:%M'),
                'client_number': failure.customer.client_number if failure.customer else None,
                'delivery_id': failure.delivery_id  # Asegúrate de que esto está en la respuesta# Número de cliente
            })

        return JsonResponse(result, safe=False)

    except AttributeError as e:
        return JsonResponse({'error': f'Error de atributo: {str(e)}'}, status=500)

    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)



@api_view(['PUT', 'POST'])
@permission_classes([AllowAny])
def update_failure(request, failure_id):
    """
    Actualizar el fallo de email con un nuevo correo electrónico y cambiar el estado.
    """
    failure = get_object_or_404(EmailNotificationFailure, id=failure_id)

    new_email = request.data.get('new_email')
    new_status = request.data.get('status')

    if new_email:
        # Actualizar el email en la tabla Customer
        customer = failure.customer
        if customer:
            customer.email = new_email
            customer.save()

    if new_status:
        # Actualizar el estado del fallo
        failure.status = new_status
        failure.save()

    return Response({"message": "Fallos de correo electrónico actualizados con éxito."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_email(request, failure_id):
    """
    Reenviar el correo electrónico fallido tras actualizar el email.
    """
    try:
        failure = get_object_or_404(EmailNotificationFailure, id=failure_id)
        print(f"Failure encontrado: {failure}")
        print(f"Customer: {failure.customer}, Email: {failure.customer.email if failure.customer else 'No tiene email'}")

        customer = failure.customer
        if not customer or not customer.email:
            print("Cliente o correo inválido")
            return Response({'error': 'El cliente no tiene un correo electrónico válido'}, status=status.HTTP_400_BAD_REQUEST)

        print(f"Failure encontrado: {failure}, Delivery: {failure.delivery}")
    # Lógica para reenviar el correo dependiendo del tipo de email que falló
        try:
            print(f"Tipo de email: {failure.email_type}")
            if failure.email_type == 'registro_incidencia':
                # Reenviar el correo de registro de incidencia
                return _reenviar_correo_incidencia(customer, failure)
            
            elif failure.email_type == 'resolucion_incidencia':
                # Reenviar el correo de resolución de incidencia
                return _reenviar_correo_resolucion(customer, failure)

            elif failure.email_type == 'albaran_incidencia':
                # Reenviar el correo de albarán con incidencia
                return _reenviar_correo_albaran(customer, failure)

            else:
                print("Tipo de correo no válido")
                return Response({'error': 'Tipo de correo no válido'}, status=status.HTTP_400_BAD_REQUEST)

        # Si el correo fue enviado correctamente, actualizar el estado a 'Contactado'
            failure.status = 'Contactado'
            failure.save()
            print("Correo reenviado con éxito.")

            return Response({"message": "Correo reenviado con éxito."}, status=status.HTTP_200_OK)

        except Exception as e:
            
            print(f"Error reenviando el correo: {str(e)}")  # Capturar el error
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        print(f"Error al procesar la solicitud de reenvío de correo: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
def get_email_failure_reasons(request):
    """
    Devuelve una lista de los motivos únicos de fallos de emails
    """
    try:
        # Obtener los motivos únicos de la tabla EmailNotificationFailure
        reasons = EmailNotificationFailure.objects.values_list('reason', flat=True).distinct()
        return JsonResponse(list(reasons), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def _reenviar_correo_incidencia(customer, failure):
    delivery = getattr(failure, 'delivery', None)
    if not delivery:
        return Response({'error': 'No se encontró el albarán relacionado con este fallo de correo.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        
        incident_number = getattr(delivery, 'incident_number', None)  # Obtener el número de incidencia

        if not incident_number:
            return Response({'error': 'No se encontró el número de incidencia asociado a este albarán.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener detalles del cliente y del albarán
        delivery = failure.delivery # Suponiendo que `failure` tiene una relación con `delivery`
        print(f"Delivery: {delivery}")
        
        send_mail(
            subject=f'Incidencia registrada: {incident_number}',
            message=f"Estimado/a {customer.name},\n\n"
                    f"Se ha registrado una incidencia con el número de albarán {delivery.fiscal_year}/{delivery.delivery_number}.\n\n"
                    f"Nuestro equipo está trabajando para resolverla lo antes posible.\n\n"
                    f"Atentamente,\n"
                    f"Departamento de Atención al Cliente\n"
                    f"952 91 61 18\n"
                    f"bahiaazul@mubak.com",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            fail_silently=False,
            html_message=f"""
                    <p>Estimado/a {delivery.customer.name},</p>
                    <p>Se ha registrado una incidencia con el número {incident_number} para su albarán {delivery.fiscal_year}/{delivery.delivery_number}. Nuestro equipo está trabajando para resolverla a la mayor brevedad posible.</p>
                    <p>Agradecemos su paciencia.</p>
                    <p>Atentamente,</p>
                    <p>WOW Málaga<br>
                    Departamento de Atención al Cliente<br>
                    <a href="tel:+34952916118">952 91 61 18</a><br>
                    <a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>

                    <hr>

                    <p>Dear {delivery.customer.name},</p>
                    <p>An issue has been registered with incident number {incident_number} for your delivery {delivery.fiscal_year}/{delivery.delivery_number}. Our team is working to resolve it as soon as possible.</p>
                    <p>Thank you for your patience.</p>
                    <p>Sincerely,</p>
                    <p>WOW Málaga<br>
                    Customer Service Department<br>
                    <a href="tel:+34952916118">+34 952 91 61 18</a><br>
                    <a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>

            """
        )

        # Actualizar estado a 'contacted'
        failure.status = 'contacted'
        failure.save()

        return Response({"message": "Correo reenviado con éxito."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



def _reenviar_correo_resolucion(customer, failure):
    delivery = getattr(failure, 'delivery', None)
    if not delivery:
        return Response({'error': 'No se encontró el albarán relacionado con este fallo de correo.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        delivery = failure.delivery
        print(f"Delivery: {delivery}")

        send_mail(
            subject=f"Resolución de incidencia - Albarán N.º {delivery.fiscal_year}/{delivery.delivery_number}",
            message=f"Estimado/a {customer.name},\n\n"
                    f"Le informamos que su incidencia ha sido resuelta con éxito para el albarán {delivery.fiscal_year}/{delivery.delivery_number}.\n\n"
                    f"Si tiene alguna duda, por favor póngase en contacto con nosotros.\n\n"
                    f"Atentamente,\n"
                    f"Departamento de Atención al Cliente\n"
                    f"952 91 61 18\n"
                    f"bahiaazul@mubak.com",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            fail_silently=False,
            html_message=f"""
                <p>Estimado/a {customer.name},</p>
                <p>Le informamos que su incidencia ha sido resuelta con éxito.</p>
                <p>Si tiene alguna duda, por favor póngase en contacto con nosotros.</p>
                <p>Atentamente,</p>
                <p>WOW Málaga<br>Departamento de Atención al Cliente<br><a href="tel:+34952916118">+34 952 91 61 18</a><br><a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>

                <hr>

                <p>Dear {customer.name},</p>
                <p>Your issue has been successfully resolved for delivery {delivery.fiscal_year}/{delivery.delivery_number}.</p>
                <p>If you have any questions, please feel free to contact us.</p>
                <p>Sincerely,</p>
                <p>WOW Málaga<br>Customer Service Department<br><a href="tel:+34952916118">+34 952 91 61 18</a><br><a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>
            """
        )

        # Actualizar estado a 'contacted'
        failure.status = 'contacted'
        failure.save()

        return Response({"message": "Correo de resolución reenviado con éxito."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _reenviar_correo_albaran(customer, failure):
    
    delivery = getattr(failure, 'delivery', None)
    if not delivery:
        return Response({'error': 'No se encontró el albarán relacionado con este fallo de correo.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        delivery = failure.delivery
        print(f"Delivery: {delivery}")# Suponiendo que failure tiene una relación con delivery
        productos_afectados = ""

        # Obtener los productos afectados si están disponibles
        if delivery.issues:
            product_details = []
            for issue in delivery.issues:
                product = Product.objects.filter(product_number=issue).first()
                if product:
                    product_details.append(f"<li>E-{product.product_number} {product.description}</li>")
                else:
                    product_details.append(f"<li>Producto con número {issue} no encontrado</li>")
            productos_afectados = "".join(product_details)
        else:
            productos_afectados = "<li>Sin detalles de productos.</li>"

        # Enviar el correo de notificación de incidencia
        send_mail(
            subject=f"Incidencia registrada - Albarán N.º {delivery.fiscal_year}/{delivery.delivery_number}",
            message=f"Estimado/a {customer.name},\n\n"
                    f"Le informamos que se ha registrado una incidencia con el número de albarán {delivery.fiscal_year}/{delivery.delivery_number}.\n\n"
                    f"A continuación se detalla la lista de productos afectados:\n"
                    f"{productos_afectados}\n\n"
                    f"Nuestro equipo está trabajando para resolver esta incidencia lo antes posible y nos pondremos en contacto con usted si necesitamos más información.\n\n"
                    f"Agradecemos su paciencia y lamentamos los inconvenientes que esto pueda ocasionar.\n\n"
                    f"Atentamente,\n"
                    f"Departamento de Atención al Cliente\n"
                    f"952 91 61 18\n"
                    f"bahiaazul@mubak.com",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            fail_silently=False,
            html_message=f"""
                <p>Estimado/a {customer.name},</p>
                <p>Le informamos que se ha registrado una incidencia en su albarán con los siguientes detalles:</p>
                <ul>
                    <li><strong>Número de Albarán:</strong> {delivery.fiscal_year}/{delivery.delivery_number}</li>
                    <li><strong>Número de Cliente:</strong> {delivery.client_number}</li>
                </ul>
                <p><strong>Productos Afectados:</strong></p>
                <ul>
                    {productos_afectados}
                </ul>
                <p>Nuestro equipo está trabajando para resolver la incidencia a la mayor brevedad posible y le contactaremos si necesitamos información adicional.</p>
                <p>Le agradecemos su paciencia y lamentamos cualquier inconveniente causado.</p>
                <p>Atentamente,</p>
                <p>WOW Málaga<br>Departamento de Atención al Cliente<br><a href="tel:+34952916118">+34 952 91 61 18</a><br><a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>

                <hr>

                <p>Dear {customer.name},</p>
                <p>An issue has been registered with your delivery:</p>
                <ul>
                    <li><strong>Delivery Number:</strong> {delivery.fiscal_year}/{delivery.delivery_number}</li>
                    <li><strong>Customer Number:</strong> {delivery.client_number}</li>
                </ul>
                <p><strong>Affected Products:</strong></p>
                <ul>
                    {productos_afectados}
                </ul>
                <p>Our team is working to resolve this issue as soon as possible, and we will contact you if we need additional information.</p>
                <p>We appreciate your patience and apologize for any inconvenience this may cause.</p>
                <p>Sincerely,</p>
                <p>WOW Málaga<br>Customer Service Department<br><a href="tel:+34952916118">+34 952 91 61 18</a><br><a href="mailto:bahiaazul@mubak.com">bahiaazul@mubak.com</a></p>
            """
        )

        # Actualizar estado a 'contacted'
        failure.status = 'contacted'
        failure.save()

        return Response({"message": "Correo de incidencia reenviado con éxito."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def count_pending_emails(request):
    """
    Devuelve el número de correos electrónicos pendientes de contacto (status='pending').
    """
    try:
        pending_count = EmailNotificationFailure.objects.filter(status='pendiente_contacto').count()
        return Response({'pending_count': pending_count}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=500)