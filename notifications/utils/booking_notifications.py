from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from bookings.models import Booking
from notifications.models import Notification
from notifications.utils.sms_utils import send_sms_from_template
from notifications.utils.email_utils import send_templated_email
from notifications.utils.whatsapp_utils import send_whatsapp_template
# from notifications.utils.whatsapp_utils import send_whatsapp_message   # (Optional future import)


def send_booking_notifications(
    booking_id: str,
    action_type: str,
    notification_list: list = None,
) -> dict:
    """
    Central notification dispatcher for booking-related events.
    
    Args:
        booking_id (str): ID of the Booking
        action_type (str): One of ("booking_created", "booking_updated", "payment_success", "payment_failed", etc.)
        notification_list (list, optional): Which channels to send. 
            Allowed values: ["sms", "email", "whatsapp"]. 
            Defaults to all enabled channels.

    Returns:
        dict: A summary of what was sent and their statuses.
    """
    try:
        booking = Booking.objects.select_related("user", "address").get(id=booking_id)
    except Booking.DoesNotExist:
        raise ValueError(f"Booking {booking_id} not found")

    user = booking.user
    summary = {"sms": None, "email": None, "whatsapp": None}

    # ✅ Default to all three if not provided
    if notification_list is None:
        notification_list = ["sms", "email", "whatsapp"]

    # ✅ Define template keys based on action_type
    # These should map to DB templates or email HTML templates
    template_map = {
        "booking_created": {
            "sms": "booking_update",
            "email": "emails/booking_created.html",
            "whatsapp": "booking_update",
            "subject": "Your Booking is Confirmed!",
        },
        "booking_updated": {
            "sms": "booking_update",
            "email": "emails/booking_created.html",
            "whatsapp": "bookingcreat",
            "subject": "Your Booking Was Updated",
        },
        "payment_success": {
            "sms": "payment_success_sms",
            "email": "emails/payment_success.html",
            "whatsapp": "payment_success_whatsapp",
            "subject": "Payment Received Successfully",
        },
        "payment_failed": {
            "sms": "payment_failed_sms",
            "email": "emails/payment_failed.html",
            "whatsapp": "payment_failed_whatsapp",
            "subject": "Payment Failed",
        },
    }

    if action_type not in template_map:
        raise ValueError(f"Unsupported action_type: {action_type}")

    templates = template_map[action_type]
    context = {
        "user": user,
        "booking": booking,
        "ref_id":booking.ref_id,
        "booking_id": booking.id,
        "name": user.first_name,
        "status":booking.customer_status,
        "final_amount": booking.final_amount,
        "scheduled_date": booking.scheduled_date,
        "scheduled_time_slot": booking.scheduled_time_slot,
        "tests":str(booking.items.count()) + " confirmed Tests",
        "payment_status":booking.payment_status,
        "base_url": getattr(settings, "BASE_URL", "https://drpathcare.com"),
    }

    # ✅ 1. SMS
    if "sms" in notification_list:
        try:
            sms_notif = send_sms_from_template(
                template_name=templates["sms"],
                user=user,
                context=context
            )
            summary["sms"] = {"status": sms_notif.status, "id": sms_notif.id}
        except Exception as e:
            Notification.objects.create(
                recipient=user,
                notification_type="sms",
                message=str(e),
                status="failed",
                error_message="Failed while sending booking SMS"
            )
            summary["sms"] = {"status": "failed", "error": str(e)}

    # ✅ 2. Email
    if "email" in notification_list:
        try:
            email_notif = send_templated_email(
                recipient=user,
                subject=templates["subject"],
                template_name=templates["email"],
                context=context,
                related_object=booking
            )
            summary["email"] = {"status": email_notif.status, "id": email_notif.id}
        except Exception as e:
            Notification.objects.create(
                recipient=user,
                notification_type="email",
                message=str(e),
                status="failed",
                error_message="Failed while sending booking email"
            )
            summary["email"] = {"status": "failed", "error": str(e)}

    # ✅ 3. WhatsApp (Optional, if integration exists)
    if "whatsapp" in notification_list:
        try:
            whatsapp_notif = send_whatsapp_template(
                user=user,
                template_name=templates["whatsapp"] if booking.customer_status != 'report_uploaded' else 'report_update',
                header_params={"name":context['name']} if booking.customer_status != 'report_uploaded' else None,
                body_params=context,
                related_object=booking,
            )

            summary["whatsapp"] = {"status": whatsapp_notif.status,"id": whatsapp_notif.id}

        except Exception as e:
            Notification.objects.create(
                recipient=user,
                notification_type="whatsapp",
                message=str(e),
                status="failed",
                error_message="Failed while sending booking WhatsApp"
            )
            summary["whatsapp"] = {"status": "failed", "error": str(e)}


    return summary
