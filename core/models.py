from django.db import models
from django.contrib.auth.models import User

class Warehouse(models.Model):
    cliente = models.ForeignKey(User, on_delete=models.CASCADE)
    wr_number = models.CharField(max_length=30, unique=True, primary_key=True)
    shipper = models.CharField(max_length=100)
    carrier = models.CharField(max_length=100)
    container_number = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    weight_lbs = models.FloatField(null=True)
    weight_kgs = models.FloatField()

    uploaded_file = models.FileField(upload_to='warehouse_files/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.weight_lbs:
            self.weight_kgs = round(self.weight_lbs * 0.453592, 3)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Warehouse {self.wr_number} - {self.cliente.username}"


class PieceWarehouse(models.Model):
    TYPE_OF = [
        ('PALLETS', 'Pallets'),
        ('CAJAS', 'Cajas'),
        ('TAMBORES', 'Tambores'),
        ('ATADOS', 'Atados'),
        ('OTRO', 'Otro'),
    ]

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='pieces')
    type_of = models.CharField(max_length=20, choices=TYPE_OF)
    quantity = models.PositiveIntegerField()
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.quantity} {self.get_type_of_display()} en {self.warehouse.wr_number}"
