import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from notifications.models import Notification, SMSTemplate

User = get_user_model()

SMS_URL = settings.SMS_URL
USERNAME = settings.SMS_USERNAME
API_KEY = settings.SMS_API_KEY


def send_sms_from_template(template_name: str, user: User, context: dict) -> Notification:
    """
    Send SMS to a user using a DB template and log the notification.
    Args:
        template_name: name of SMSTemplate in DB (e.g. "login_otp")
        user: Django User object (must have `mobile` field)
        context: dict of values to fill in template message (e.g. {"otp": "123456", "name": "Aloukik"})
    """
    try:
        template = SMSTemplate.objects.get(name=template_name, is_active=True)
    except SMSTemplate.DoesNotExist:
        return Notification.objects.create(
            recipient=user,
            notification_type="sms",
            message=f"Template {template_name} not found",
            status="failed",
            error_message="SMSTemplate missing in DB",
        )

    # 🧩 Fill placeholders
    try:
        message = template.message.format(**context)
    except KeyError as e:
        return Notification.objects.create(
            recipient=user,
            notification_type="sms",
            message=f"Template error: missing {str(e)}",
            status="failed",
            error_message=f"Missing placeholder {str(e)} in template",
        )

    # 📬 Create notification log
    notification = Notification.objects.create(
        recipient=user,
        notification_type="sms",
        message=message,
        status="pending",
    )

    # 📦 Prepare request payload
    payload = {
        "username": USERNAME,
        "message": message,
        "sendername": template.sender_name,
        "smstype": template.sms_type,
        "numbers": getattr(user, "mobile", None),
        "apikey": API_KEY,
        "peid": template.peid,
        "templateid": template.template_id,
    }

    if not payload["numbers"]:
        notification.status = "failed"
        notification.error_message = "User has no mobile number"
        notification.save()
        return notification

    # 🚀 Send SMS
    try:
        response = requests.get(SMS_URL, params=payload, timeout=10)
        response_text = response.text

        if response.status_code == 200 and "success" in response_text.lower():
            notification.status = "sent"
        else:
            notification.status = "failed"
            notification.error_message = response_text

    except Exception as e:
        notification.status = "failed"
        notification.error_message = str(e)

    notification.save()
    return notification
