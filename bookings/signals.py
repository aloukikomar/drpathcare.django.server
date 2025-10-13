import threading
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Booking
from notifications.utils.booking_notifications import send_booking_notifications


# ============================================================
# 🔹 Utility to generate human-readable booking ref_id
# ============================================================
def generate_ref_id_for_booking(instance: Booking):
    """
    Generate a human-readable reference ID for a booking.
    Format: dpYYMMDDXXXX
    - dp: static prefix
    - YYMMDD: booking creation date
    - XXXX: daily sequential number
    """
    if instance.ref_id:
        return instance.ref_id

    booking_date = instance.created_at.date() if instance.created_at else timezone.now().date()
    date_str = booking_date.strftime("%y%m%d")
    prefix = "dp"

    # Count only bookings that already have a ref_id (so no duplication)
    today_count = (
        Booking.objects.filter(created_at__date=booking_date)
        .exclude(ref_id__isnull=True)
        .count()
        + 1
    )

    sequence = str(today_count).zfill(4)
    ref_id = f"{prefix}{date_str}{sequence}"
    instance.ref_id = ref_id
    return ref_id


# ============================================================
# 🔹 Pre-save signal to ensure ref_id is generated
# ============================================================
@receiver(pre_save, sender=Booking)
def pre_save_generate_ref_id(sender, instance, **kwargs):
    """Automatically generate ref_id for new bookings if not present."""
    if not instance.ref_id:
        generate_ref_id_for_booking(instance)

# ============================================================
# 🔹 Pre-save signal to capture old values
# ============================================================
@receiver(pre_save, sender=Booking)
def capture_old_booking_state(sender, instance, **kwargs):
    """
    Store old values of key fields before save, for comparison in post_save.
    """
    if not instance.pk:
        return  # New booking — nothing to compare yet

    try:
        old = Booking.objects.get(pk=instance.pk)
        instance._old_status = old.status
        instance._old_payment_status = old.payment_status
    except Booking.DoesNotExist:
        instance._old_status = None
        instance._old_payment_status = None


# ============================================================
# 🔹 Post-save signal to send booking notifications
# ============================================================
@receiver(post_save, sender=Booking)
def post_save_booking_notifications(sender, instance: Booking, created, **kwargs):
    """
    Trigger notifications asynchronously after booking creation or status/payment update.
    """
    def _send_notifications():
        try:
            if created:
                # ✅ New booking created
                send_booking_notifications(str(instance.id), "booking_created")
            else:
                # ✅ Compare with captured old values
                old_status = getattr(instance, "_old_status", None)
                old_payment_status = getattr(instance, "_old_payment_status", None)

                if (
                    old_status != instance.status
                    or old_payment_status != instance.payment_status
                ):
                    send_booking_notifications(str(instance.id), "booking_updated")

        except Exception as e:
            logger.error(f"Booking notification failed: {e}")

    # Run asynchronously so it never blocks booking creation
    threading.Thread(target=_send_notifications, daemon=True).start()