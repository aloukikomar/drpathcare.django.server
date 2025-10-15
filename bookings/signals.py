import threading
import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
from .models import Booking
from notifications.utils.booking_notifications import send_booking_notifications

logger = logging.getLogger(__name__)

# ============================================================
# 🔹 Generate human-readable booking ref_id
# ============================================================
def generate_ref_id_for_booking(instance: Booking):
    if instance.ref_id:
        return instance.ref_id

    booking_date = instance.created_at.date() if instance.created_at else timezone.now().date()
    date_str = booking_date.strftime("%y%m%d")
    prefix = "dp"

    today_count = (
        Booking.objects.filter(created_at__date=booking_date)
        .exclude(ref_id__isnull=True)
        .count()
        + 1
    )

    sequence = str(today_count).zfill(4)
    instance.ref_id = f"{prefix}{date_str}{sequence}"
    return instance.ref_id


@receiver(pre_save, sender=Booking)
def pre_save_generate_ref_id(sender, instance, **kwargs):
    if not instance.ref_id:
        generate_ref_id_for_booking(instance)


# ============================================================
# 🔹 Capture old state before save
# ============================================================
@receiver(pre_save, sender=Booking)
def capture_old_booking_state(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Booking.objects.get(pk=instance.pk)
        instance._old_status = old.status
        instance._old_payment_status = old.payment_status
        instance._old_customer_status = old.customer_status
    except Booking.DoesNotExist:
        instance._old_status = None
        instance._old_payment_status = None
        instance._old_customer_status = None


# ============================================================
# 🔹 Unified post-save handler (status sync + notifications)
# ============================================================
@receiver(post_save, sender=Booking)
def post_save_booking_handler(sender, instance: Booking, created, **kwargs):
    """
    Unified handler that:
    - Updates customer_status
    - Auto-sets status to 'payment_collected' on payment success
    - Sends booking notifications (created/updated)
    """

    def _process_after_commit():
        try:
            old_status = getattr(instance, "_old_status", None)
            old_payment_status = getattr(instance, "_old_payment_status", None)
            old_customer_status = getattr(instance, "_old_customer_status", None)

            refreshed = Booking.objects.filter(pk=instance.pk).first()
            if not refreshed:
                return

            # 🟢 Step 1: Handle new booking
            if created:
                send_booking_notifications(str(instance.id), "booking_created")
                return

            # 🟢 Step 2: Define status-to-customer_status mapping
            customer_status_map = {
                "verified": "verified",
                "manager_assigned": "verified",
                "field_agent_assigned": "verified",
                "payment_collected": "payment_collected",
                "sample_collected": "sample_collected",
                "report_uploaded": "report_uploaded",
                "health_manager_assigned": "report_uploaded",
                "dietitian_assigned": "report_uploaded",
                "completed": "completed",
                "cancelled": "cancelled",
            }

            # 🟢 Step 3: Handle payment success
            if (
                old_payment_status != instance.payment_status
                and instance.payment_status == "success"
            ):
                Booking.objects.filter(pk=instance.pk).update(
                    status="payment_collected",
                    customer_status="payment_collected",
                )
                logger.info(f"Booking {instance.id}: marked as payment_collected")
                # Still send notification after marking success
                send_booking_notifications(str(instance.id), "booking_updated")
                return

            # 🟢 Step 4: Sync customer_status with booking status
            new_customer_status = customer_status_map.get(instance.status)
            if (
                new_customer_status
                and refreshed.customer_status != new_customer_status
            ):
                Booking.objects.filter(pk=instance.pk).update(customer_status=new_customer_status)

            # 🟢 Step 5: Send notification only if key fields changed
            if (
                old_status != instance.status
                or old_payment_status != instance.payment_status
                or old_customer_status != instance.customer_status
            ):
                send_booking_notifications(str(instance.id), "booking_updated")

        except Exception as e:
            logger.error(f"[Booking Signal] Error processing {instance.id}: {e}")

    # Run after commit, async (so no blocking)
    transaction.on_commit(lambda: threading.Thread(target=_process_after_commit, daemon=True).start())
