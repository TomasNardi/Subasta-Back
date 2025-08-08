from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProductSerializer
from django.contrib.auth.models import User
from django.http import JsonResponse, Http404, HttpResponse



@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])  # Permite subir imagen
def crear_subasta_api(request):
    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Cree el superusuario desde el backend, con ruta por RENDER

def create_superuser(request):
    try:
        username = "BifyAdmin"
        password = "admin1999"
        email = "admin@example.com"

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username, email=email, password=password
            )
            return HttpResponse("Superusuario creado con éxito.")
        else:
            return HttpResponse("El superusuario ya existe.")
    except Exception as e:
        return HttpResponse(f"Error: {e}")
