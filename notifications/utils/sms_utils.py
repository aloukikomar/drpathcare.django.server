import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from notifications.models import Notification, SMSTemplate
from typing import Tuple, Optional

User = get_user_model()

SMS_URL = settings.SMS_URL
USERNAME = settings.SMS_USERNAME
API_KEY = settings.SMS_API_KEY


def send_otp_sms(mobile: str, otp_code: str) -> Tuple[bool, str, Notification]:
    """
    Send OTP SMS using the 'OTP' SMSTemplate but call the low-level send_sms().
    Returns: (success, response_text, Notification)
    """
    # 1) Get template
    try:
        template = SMSTemplate.objects.get(name="OTP", is_active=True)
    except SMSTemplate.DoesNotExist:
        # create a failed notification for audit
        notif = Notification.objects.create(
            recipient=None,
            notification_type="sms",
            message=f"Missing OTP template",
            status="failed",
            error_message="SMSTemplate OTP not found",
        )
        return False, "SMSTemplate not found", notif

    # 2) Render message
    try:
        message = template.message.format(otp=otp_code, mobile=mobile)
    except Exception as e:
        notif = Notification.objects.create(
            recipient=None,
            notification_type="sms",
            message=f"Template render error",
            status="failed",
            error_message=str(e),
        )
        return False, f"Template render error: {e}", notif

    # 3) Try to find user by mobile (may be None)
    user = User.objects.filter(mobile=mobile).first()
    notif=''
    if user :
        # 4) Create pending notification
        notif = Notification.objects.create(
            recipient=user,
            notification_type="sms",
            message=message,
            status="pending",
        )

    # 5) Build raw payload expected by send_sms()
    payload = {
        "username": USERNAME,
        "message": message,
        "sendername": getattr(template, "sender_name", ""),
        "smstype": getattr(template, "sms_type", ""),   # e.g. 'TRANS'
        "numbers": mobile,
        "apikey": API_KEY,
        "peid": getattr(template, "peid", ""),
        "templateid": getattr(template, "template_id", ""),
    }

    # 6) Call send_sms (low-level function)
    success, resp_text = send_sms(payload)

    if user :
        # 7) Update notification based on result
        notif.status = "sent" if success else "failed"
        notif.error_message = None if success else (resp_text or "Unknown error")
        notif.save(update_fields=["status", "error_message"])

    return success, resp_text, notif



# -------------------------------------------------------------------
# 🧩 Child function — generic SMS sender
# -------------------------------------------------------------------
def send_sms(payload: dict) -> tuple[bool, str]:
    """
    Sends SMS via the configured SMS API.
    Args:
        payload: dict with fields:
            {
                "username": str,
                "message": str,
                "sendername": str,
                "smstype": str,
                "numbers": str,  # comma-separated or single mobile
                "apikey": str,
                "peid": str,
                "templateid": str
            }

    Returns:
        (success: bool, response_text: str)
    """
    try:
        response = requests.get(SMS_URL, params=payload, timeout=10)
        response_text = response.text

        if response.status_code == 200 and "success" in response_text.lower():
            return True, response_text
        else:
            return False, response_text

    except Exception as e:
        return False, str(e)


# -------------------------------------------------------------------
# 🧩 Parent function — send SMS from a DB template and log notification
# -------------------------------------------------------------------
def send_sms_from_template(template_name: str, user: User, context: dict) -> Notification:
    """
    Send SMS to a user using a DB template and log the notification.

    Args:
        template_name (str): Name of SMSTemplate in DB (e.g. "login_otp")
        user (User): Django User object (must have `mobile` field)
        context (dict): Values to fill placeholders in template.message
                        (e.g. {"otp": "123456", "name": "Aloukik"})

    Returns:
        Notification: Saved notification record (status = sent | failed)
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

    # 🧠 Fill message placeholders
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

    # 🪵 Log pending notification
    notification = Notification.objects.create(
        recipient=user,
        notification_type="sms",
        message=message,
        status="pending",
    )

    # 🚧 Build payload (raw data for `send_sms`)
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

    # 🚀 Send SMS via child function
    success, response_text = send_sms(payload)

    notification.status = "sent" if success else "failed"
    notification.error_message = None if success else response_text
    notification.save()

    return notification
