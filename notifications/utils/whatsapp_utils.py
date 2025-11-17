import requests
import json
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

# ===========================================================
# CONFIGURATION
# ===========================================================
GETA_API_URL = "https://api-whatsapp.geta.ai/api/v1/whatsapp/send_template_message"
GETA_API_KEY = getattr(settings, "GETA_API_KEY", None)  # store your long key in settings.py as GETA_API_KEY

# ===========================================================
# CORE FUNCTION
# ===========================================================
def send_whatsapp_template(
    user: User,
    template_name: str,
    header_params: list[str] | None = None,
    body_params: list[str] | None = None,
    related_object=None
) -> Notification:
    """
    Send WhatsApp message via GETA.AI template system.

    Args:
        user: Django User instance (must have .mobile)
        template_name: WhatsApp template name (e.g. 'booking_update', 'bookingcreat')
        header_params: list of header placeholders (optional)
        body_params: list of body placeholders (in template order)
        related_object: (optional) booking/payment etc for Notification relation

    Returns:
        Notification instance
    """
    if not GETA_API_KEY:
        raise ValueError("GETA_API_KEY not configured in settings.py")

    if not getattr(user, "mobile", None):
        return Notification.objects.create(
            recipient=user,
            notification_type="whatsapp",
            message=f"User has no mobile number",
            status="failed",
        )

    # =======================================================
    # Construct template components
    # =======================================================
    components = []

    if header_params:
        components.append({
            "type": "header",
            "parameters": [{"type": "text", "text": str(header_params['name'])}],
        })

    if body_params:
        if template_name=='booking_update':
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(body_params['ref_id'])},
                    {"type": "text", "text": str(body_params['status'])},
                    {"type": "text", "text": str(body_params['final_amount'])},
                    {"type": "text", "text": str(body_params['scheduled_date'])},
                    {"type": "text", "text": str(body_params['scheduled_time_slot'])},
                ],
            })
        else:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(body_params['ref_id'])},
                    {"type": "text", "text": str(body_params['status'])},
                    {"type": "text", "text": str(body_params['tests'])},
                    {"type": "text", "text": str(body_params['payment_status'])},
                    {"type": "text", "text": str(body_params['final_amount'])},
                    {"type": "text", "text": str(body_params['scheduled_date'])},
                    {"type": "text", "text": str(body_params['scheduled_time_slot'])},
                ],
            })
    payload = {
        "to": "91"+str(user.mobile),  # must be international format (e.g. 919876543210)
        "content": {
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": components,
            },
        },
    }

    headers = {
        "Content-Type": "application/json",
        "geta-host": GETA_API_KEY,
    }

    # Create pending notification
    notif = Notification.objects.create(
        recipient=user,
        notification_type="whatsapp",
        message=json.dumps(payload),
        status="pending",
        content_type=ContentType.objects.get_for_model(related_object) if related_object else None,
        object_id=related_object.pk if related_object else None,
    )

    # =======================================================
    # Send request
    # =======================================================
    try:
        response = requests.post(GETA_API_URL, headers=headers, json=payload, timeout=15)
        response_text = response.text

        if response.status_code == 200 and "success" in response_text.lower():
            notif.status = "sent"
        else:
            notif.status = "failed"
            notif.error_message = response_text

    except Exception as e:
        notif.status = "failed"
        notif.error_message = str(e)

    notif.save()
    return notif
