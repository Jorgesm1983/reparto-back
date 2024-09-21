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
from rest_framework.decorators import api_view
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated

# from .models import Delivery

import os
    
class DeliveryCreateView(APIView):
    permission_classes = [IsAuthenticated]  # Requiere autenticación
    
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    
    def post(self, request, *args, **kwargs):

        if request.data.get('visit_type') in ['verification', 'resolution']:
            request.data.pop('issues', None)
        
        serializer = DeliverySerializer(data=request.data)
        if serializer.is_valid():
            delivery = serializer.save(user=request.user)  # Asociar el usuario autenticado

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        

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

