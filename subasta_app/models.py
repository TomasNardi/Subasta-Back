from django.db import models


# Aca van los modelos - en caso de nececistar realizar Foreing keys consultarle al ketson 

class Title(models.Model): 
    title = models.CharField(max_length=200)

class Product(models.Model): 
    image = models.ImageField(upload_to="temp/")  # podés cambiar "temp/" por algo como "subastas/"
    title = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.title} - ${self.price}"