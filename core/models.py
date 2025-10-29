from django.db import models
from django.contrib.auth.models import User
import mimetypes, os

ADMIN_PANEL_COLUMN_KEYS = [
    "wr",
    "cliente",
    "shipper",
    "carrier",
    "container",
    "foots",
    "tracking",
    "invoice",
    "po",
    "fecha",
    "acciones",
]


def default_admin_column_state():
    return {key: True for key in ADMIN_PANEL_COLUMN_KEYS}


CLIENT_PANEL_COLUMN_KEYS = [
    "wr",
    "carrier",
    "shipper",
    "weight",
    "status",
    "created",
    "actions",
]


def default_client_column_state():
    return {key: True for key in CLIENT_PANEL_COLUMN_KEYS}

class Warehouse(models.Model):

    STATUS = [
        ('PENDIENTE', 'Pendiente'),
        ('LISTO', 'Listo')
    ]

    cliente = models.ForeignKey(User, on_delete=models.CASCADE)
    wr_number = models.CharField(max_length=30, unique=True, primary_key=True)
    shipper = models.CharField(max_length=100)
    carrier = models.CharField(max_length=100)
    container_number = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    weight_lbs = models.FloatField(null=True)
    weight_kgs = models.FloatField(null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='PENDIENTE')
    # Nuevos campos 
    foots = models.FloatField(null=True)
    tracking = models.CharField(max_length=100, null=True)
    invoice_number = models.CharField(max_length=100, null=True)
    po = models.CharField(max_length=100, blank=True)


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


# core/models.py
from django.core.exceptions import ValidationError

class DispatchRequest(models.Model):
    METHOD_CHOICES = [
        ("MARITIMO", "Marítimo"),
        ("AEREO", "Aéreo"),
        ("TERRESTRE", "Terrestre"),
    ]
    STATUS_CHOICES = [
        ("PENDIENTE", "Pendiente de revisión"),
        ("APROBADO", "Aprobado / En proceso"),
        ("RECHAZADO", "Rechazado"),
        ("COMPLETADO", "Completado"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dispatch_requests")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    invoice = models.FileField(upload_to="invoices/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDIENTE")
    created_at = models.DateTimeField(auto_now_add=True)

    # B/L subido por admin (obligatorio al aprobar)
    bill_of_lading = models.FileField(upload_to="bol/", blank=True, null=True)
    bol_uploaded_at = models.DateTimeField(blank=True, null=True)

    def clean(self):
        # Si intenta marcar como APROBADO o COMPLETADO, debe existir B/L
        if self.status in ("APROBADO", "COMPLETADO") and not self.bill_of_lading:
            raise ValidationError("Debes subir el Bill of Lading para aprobar o completar la solicitud.")

    def save(self, *args, **kwargs):
        self.full_clean()  # asegura validación
        return super().save(*args, **kwargs)


class DispatchRequestItem(models.Model):
    dispatch = models.ForeignKey(DispatchRequest, on_delete=models.CASCADE, related_name="items")
    warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, related_name="dispatch_items")

    class Meta:
        unique_together = ("dispatch", "warehouse")

    def __str__(self):
        return f"REQ {self.dispatch_id} → WR {self.warehouse_id}"
    
class PieceItem(models.Model):
    """
    Unidad física individual perteneciente a una PieceWarehouse (grupo).
    Aquí van peso y medidas unitarias.
    """
    piece = models.ForeignKey(PieceWarehouse, on_delete=models.CASCADE, related_name='items')
    # Identificador opcional visible en UI (1..N). No único global, solo dentro del grupo.
    index = models.PositiveIntegerField(default=1)

    # Medidas y peso individuales
    weight_lbs = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight_kgs = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    length_cm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width_cm  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        # Evita dos items con el mismo index dentro del mismo grupo
        unique_together = ('piece', 'index')
        ordering = ('piece', 'index')

    def save(self, *args, **kwargs):
        if self.weight_lbs and not self.weight_kgs:
            self.weight_kgs = round(float(self.weight_lbs) * 0.453592, 3)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.piece.warehouse.wr_number} - {self.piece.get_type_of_display()} #{self.index}"


class WarehouseDocument(models.Model):
    warehouse = models.ForeignKey("Warehouse", on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="warehouse_docs/%Y/%m/")
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ("-uploaded_at", "id")

    def save(self, *args, **kwargs):
        # autocompletar metadatos
        if self.file and not self.original_name:
            self.original_name = os.path.basename(self.file.name)
        if self.file and hasattr(self.file, "file") and hasattr(self.file.file, "size"):
            self.size_bytes = self.file.file.size
        if self.file and not self.content_type:
            guess, _ = mimetypes.guess_type(self.file.name)
            self.content_type = guess or "application/octet-stream"
        super().save(*args, **kwargs)

    # helpers UI
    @property
    def is_image(self):
        return (self.content_type or "").startswith("image/")

    @property
    def filename(self):
        return os.path.basename(self.original_name or self.file.name)


class AdminColumnPreference(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="admin_column_preference",
    )
    columns = models.JSONField(default=default_admin_column_state)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferencia de columnas (admin)"
        verbose_name_plural = "Preferencias de columnas (admin)"

    def __str__(self):
        return f"Columnas admin - {self.user.username}"


class ClientColumnPreference(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="client_column_preference",
    )
    columns = models.JSONField(default=default_client_column_state)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferencia de columnas (cliente)"
        verbose_name_plural = "Preferencias de columnas (cliente)"

    def __str__(self):
        return f"Columnas cliente - {self.user.username}"
