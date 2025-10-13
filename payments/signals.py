from django.db.models.signals import post_save
from django.dispatch import receiver
from payments.models import BookingPayment
from payments.utils import sync_booking_from_latest_payment

@receiver(post_save, sender=BookingPayment)
def sync_booking_on_payment_save(sender, instance: BookingPayment, **kwargs):
    """
    Whenever a BookingPayment is created or updated,
    automatically sync the Booking payment_status & method.
    """
    sync_booking_from_latest_payment(instance.booking)
