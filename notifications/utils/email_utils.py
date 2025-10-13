from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType
from django.utils.html import strip_tags
from django.conf import settings
from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()


def send_templated_email(
    recipient,
    subject: str,
    template_name: str,
    context: dict,
    related_object=None
) -> Notification:
    """
    Sends a templated HTML email and logs it in Notification table.

    Args:
        recipient (User or str): User object or email string
        subject (str): Email subject
        template_name (str): Path to HTML template (e.g. "emails/booking_confirmation.html")
        context (dict): Context for rendering template
        related_object (Model, optional): Related model instance (Booking, Payment, etc.)

    Returns:
        Notification: The created Notification object
    """

    # ✅ Resolve recipient
    if hasattr(recipient, "email"):
        email = recipient.email
        user = recipient
    else:
        email = recipient
        user = None

    # 📧 Render HTML + text fallback
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    # ✉️ Create email message
    email_msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email="DrPathCare <"+settings.DEFAULT_FROM_EMAIL+">",
        to=[email],
    )
    email_msg.attach_alternative(html_content, "text/html")

    # 📤 Send email
    try:
        email_msg.send(fail_silently=False)
        status = "sent"
        error_message = None
    except Exception as e:
        status = "failed"
        error_message = str(e)

    # 🪵 Log notification
    notification = Notification.objects.create(
        recipient=user,
        notification_type="email",
        subject=subject,
        message=text_content,
        status=status,
        error_message=error_message,
        content_type=ContentType.objects.get_for_model(related_object) if related_object else None,
        object_id=related_object.pk if related_object else None,
    )
    return notification
