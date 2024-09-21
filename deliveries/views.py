from rest_framework import viewsets
from rest_framework import status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Delivery, DeliveryImage, IssuePhoto
from .serializers import DeliverySerializer
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
# from .models import Delivery

import os

class DeliveryCreateView(APIView):
    
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    
    def post(self, request, *args, **kwargs):
        print("Datos de la solicitud:", request.data)
        if request.data.get('visit_type') in ['verification', 'resolution']:
            request.data.pop('issues', None)
        
        serializer = DeliverySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        print("Errores", serializer.errors)  # Imprime los errores de validación
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

