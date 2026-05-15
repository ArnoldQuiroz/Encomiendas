"""
📧 Notificaciones automáticas por email cuando cambia el estado.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def notificar_cambio_estado(encomienda, estado_anterior):
    """
    Envía email al destinatario y/o remitente cuando cambia el estado.
    Es 'best-effort': si falla no rompe el flujo.
    """
    if not encomienda.destinatario.email and not encomienda.remitente.email:
        return

    asunto_map = {
        'TR': f'🚚 Tu paquete {encomienda.codigo} está en camino',
        'DE': f'📍 Tu paquete {encomienda.codigo} llegó a destino',
        'EN': f'✅ Tu paquete {encomienda.codigo} fue entregado',
        'DV': f'↩️ Tu paquete {encomienda.codigo} fue devuelto',
    }
    asunto = asunto_map.get(encomienda.estado, f'Actualización de {encomienda.codigo}')

    contexto = {
        'encomienda': encomienda,
        'estado_anterior': estado_anterior,
        'tracking_url': f'http://localhost:8000/track/{encomienda.codigo}/',
    }

    try:
        html_content = render_to_string('emails/cambio_estado.html', contexto)
        text_content = render_to_string('emails/cambio_estado.txt', contexto)

        # Construir lista de destinatarios
        destinatarios = []
        if encomienda.destinatario.email:
            destinatarios.append(encomienda.destinatario.email)
        if encomienda.remitente.email and encomienda.remitente.email not in destinatarios:
            destinatarios.append(encomienda.remitente.email)

        if not destinatarios:
            return

        msg = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        pass  # Nunca romper el cambio de estado por un error de email
