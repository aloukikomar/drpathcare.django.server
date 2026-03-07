import razorpay
from django.conf import settings
from decimal import Decimal
from payments.models import BookingPayment
from bookings.models import Booking
from django.core.exceptions import ObjectDoesNotExist

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_payment_link(booking: Booking, amount: Decimal, email: str, phone: str) -> BookingPayment:
    """
    Creates a Razorpay payment link and stores a BookingPayment record.

    Args:
        booking: Booking object for which payment is being initiated.
        amount: Decimal amount (in INR) to charge.
        email: Customer email address.
        phone: Customer phone number.

    Returns:
        BookingPayment: The created payment record with link & gateway details.
    """
    if not booking:
        raise ValueError("Booking object is required")
    if not amount or amount <= 0:
        raise ValueError("Amount must be a positive decimal")

    amount_in_paise = int(amount * 100)  # Razorpay expects amount in paise

    # 🧾 Create a payment link via Razorpay
    payment_link_data = client.payment_link.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "description": f"Payment for Booking {booking.id}",
        "customer": {
            "name": f"{booking.user.first_name} {booking.user.last_name}".strip(),
            "email": email,
            "contact": phone,
        },
        "notify": {"sms": True, "email": True},
        "reminder_enable": True,
        "callback_url": f"{settings.BASE_URL}/api/payment-confirmation/{booking.id}",  # ✅ Use your actual callback URL here
        "callback_method": "get",
    })

    # 🔐 Extract useful fields from Razorpay response
    payment_link_url = payment_link_data.get("short_url")
    razorpay_order_id = payment_link_data.get("id")

    # 💾 Save payment record in DB
    payment = BookingPayment.objects.create(
        booking=booking,
        amount=amount,
        status="initiated",
        method="online",  # Or "razorpay" if you prefer
        payment_link=payment_link_url,
        gateway_order_id=razorpay_order_id,
        gateway_response=payment_link_data,
        remarks="Payment link created via Razorpay",
    )

    return payment


def refresh_booking_payment_status(payment: BookingPayment) -> BookingPayment:
    """
    🔄 Fetch and update latest Razorpay payment link status for a BookingPayment.
    """
    if not payment.gateway_order_id:
        raise ValueError("Payment record does not have a provider_order_id.")

    try:
        # 1️⃣ Fetch payment link from Razorpay
        payment_link = client.payment_link.fetch(payment.gateway_order_id)

        # 2️⃣ Map Razorpay status to internal status
        status_map = {
            "created": "initiated",
            "issued": "initiated",
            "paid": "success",
            "cancelled": "failed",
            "expired": "failed",
        }
        new_status = status_map.get(payment_link.get("status"), "initiated")

        # 3️⃣ Update payment fields
        payment.gateway_response = payment_link
        payment.status = new_status

        # 4️⃣ If Razorpay returned payment IDs, capture first one
        payments_list = payment_link.get("payments", [])
        if payments_list:
            payment.transaction_id = payments_list[0].get("id")

        payment.remarks = f"Status refreshed from Razorpay: {payment_link.get('status')}"
        payment.save()

        return payment

    except razorpay.errors.BadRequestError as e:
        raise ValueError(f"Razorpay BadRequest: {str(e)}")
    except razorpay.errors.ServerError as e:
        raise ValueError(f"Razorpay ServerError: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error refreshing payment status: {str(e)}")


def refresh_latest_payment_for_booking(booking_id: str) -> BookingPayment:
    """
    🔄 Get the latest BookingPayment for a booking and refresh its status.
    """
    try:
        latest_payment = (
            BookingPayment.objects.filter(booking_id=booking_id)
            .order_by("-created_at")
            .first()
        )
        if not latest_payment:
            raise ObjectDoesNotExist("No payment found for this booking.")

        return refresh_booking_payment_status(latest_payment)

    except ObjectDoesNotExist as e:
        raise ValueError(str(e))



def sync_booking_from_latest_payment(booking: Booking) -> None:
    """
    Syncs a Booking's payment status and method from its latest BookingPayment.
    - If no payment exists, does nothing.
    - If latest payment is success/failed, updates Booking accordingly.
    """
    latest_payment = (
        BookingPayment.objects.filter(booking=booking)
        .order_by("-created_at")
        .first()
    )

    if not latest_payment:
        return

    Booking.objects.filter(pk=booking.pk).update(
        payment_status=latest_payment.status,
        payment_method=latest_payment.method
    )