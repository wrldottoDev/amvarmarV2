# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import Warehouse

@receiver(post_save, sender=Warehouse)
def send_warehouse_notification(sender, instance, created, **kwargs):
    """Enviar correo cuando se crea un nuevo warehouse"""
    if created:
        subject = f"Nuevo Warehouse creado — WR{instance.wr_number}"
        recipient = instance.cliente.email

        # cuerpo del mensaje
        context = {
            "username": instance.cliente.username,
            "wr_number": instance.wr_number,
            "shipper": instance.shipper,
            "carrier": instance.carrier,
            "created_at": instance.created_at,
        }

        message = render_to_string("emails/new_warehouse.txt", context)

        send_mail(
            subject=subject,
            message=message,
            from_email=None,  # usa DEFAULT_FROM_EMAIL
            recipient_list=[recipient],
            fail_silently=False,
        )
