from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProductSerializer
from django.contrib.auth.models import User
from django.http import JsonResponse, Http404, HttpResponse
from django.db import transaction
from rest_framework.parsers import JSONParser




@api_view(["GET"])
def keep_alive(request):
    if request.method == "GET":
        return Response(status=200)
    else:
        return Response(status=400)
     
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def crear_subasta_api(request):
    productos = []
    i = 0
    while True:
        key_title = f'productos[{i}][title]'
        key_price = f'productos[{i}][price]'
        key_image = f'productos[{i}][image]'

        if key_title in request.data:
            producto_data = {
                'title': request.data.get(key_title),
                'price': request.data.get(key_price),
                'image': request.data.get(key_image),
            }
            productos.append(producto_data)
            i += 1
        else:
            break

    if not productos:
        return Response({"error": "No products received"}, status=400)

    with transaction.atomic():
        for producto_data in productos:
            serializer = ProductSerializer(data=producto_data)
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(serializer.errors, status=400)

    return Response({"message": "Todos los productos cargados"}, status=201)


# # Cree el superusuario desde el backend, con ruta por RENDER

# def create_superuser(request):
#     try:
#         username = "BifyAdmin"
#         password = "admin1999"
#         email = "admin@example.com"

#         if not User.objects.filter(username=username).exists():
#             User.objects.create_superuser(
#                 username=username, email=email, password=password
#             )
#             return HttpResponse("Superusuario creado con éxito.")
#         else:
#             return HttpResponse("El superusuario ya existe.")
#     except Exception as e:
#         return HttpResponse(f"Error: {e}")
