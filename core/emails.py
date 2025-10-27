from django.core.mail import EmailMessage
from django.conf import settings

def send_credentials_email(user, raw_password):
    subject = "Tus credenciales de acceso - Amvarmar"
    body = (
        f"Hola {user.get_full_name() or user.username},\n\n"
        f"Te creamos un usuario en Amvarmar.\n\n"
        f"Usuario: {user.username}\n"
        f"Contraseña temporal: {raw_password}\n\n"
        f"Por seguridad, cambia tu contraseña al iniciar sesión en la plataforma.\n\n"
        f"Saludos,\nAmvarmar"
    )
    EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email]).send(fail_silently=False)

def send_dispatch_request_email_to_admin(dispatch):
    # Listado de WRs
    wr_list = [
        (it.warehouse.wr_number if hasattr(it.warehouse, "wr_number") else str(it.warehouse))
        for it in dispatch.items.select_related("warehouse").all()
    ]
    wr_str = ", ".join(wr_list) if wr_list else "(sin items?)"

    subject = f"[Amvarmar] Solicitud de despacho #{dispatch.id}"
    body = (
        f"Usuario: {dispatch.user.get_full_name() or dispatch.user.username}\n"
        f"Método: {dispatch.get_method_display()}\n"
        f"Warehouses: {wr_str}\n"
        f"Fecha: {dispatch.created_at:%Y-%m-%d %H:%M}\n"
        f"Revisar en el panel de administración."
    )
    to = [email for _, email in settings.ADMINS] or ["ottodev.1604@gmail.com"]
    msg = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, to)
    if dispatch.invoice:
        msg.attach_file(dispatch.invoice.path)
    msg.send(fail_silently=False)

def send_dispatch_received_email_to_user(dispatch):
    subject = "Recibimos tu solicitud de despacho - Amvarmar"
    body = (
        f"Hola {dispatch.user.get_full_name() or dispatch.user.username},\n\n"
        f"Recibimos tu solicitud para despachar {dispatch.items.count()} warehouse(s).\n"
        f"Método: {dispatch.get_method_display()}\n"
        f"Te avisaremos cuando esté aprobado y te enviaremos tu B/L.\n\n"
        f"Saludos,\nAmvarmar"
    )
    EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [dispatch.user.email]).send(fail_silently=True)


from django.core.mail import EmailMessage
from django.conf import settings

def send_bol_email_to_user(dispatch):
    if not dispatch.bill_of_lading or not dispatch.user.email:
        return  # nada que enviar

    # Lista de WR Numbers
    wr_list = [
        getattr(it.warehouse, "wr_number", str(it.warehouse))
        for it in dispatch.items.select_related("warehouse").all()
    ]
    wr_str = ", ".join(wr_list) if wr_list else "(sin warehouses)"

    subject = f"Bill of Lading - Solicitud #{dispatch.id}"
    body = (
        f"Hola {dispatch.user.get_full_name() or dispatch.user.username},\n\n"
        f"Tu solicitud de despacho #{dispatch.id} ha sido aprobada.\n"
        f"Método: {dispatch.get_method_display()}\n"
        f"Warehouses: {wr_str}\n\n"
        f"Adjuntamos tu Bill of Lading (B/L).\n\n"
        f"Saludos,\nAmvarmar"
    )

    msg = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [dispatch.user.email])
    msg.attach_file(dispatch.bill_of_lading.path)
    msg.send(fail_silently=False)