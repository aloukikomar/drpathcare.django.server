from django.shortcuts import render, get_object_or_404
from django.views import View
from bookings.models import Booking

class BookingPublicDetailView(View):
    """
    Public view for booking details accessed by Booking UUID.
    Example: /booking-details/2f4242f0-39ac-48b8-8d47-430a4d1a00f5/
    """

    template_name = "bookings/booking_public_view.html"

    def get(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("user", "address")
            .prefetch_related("items__lab_test", "items__profile", "items__package"),
            id=booking_id,
        )

        context = {
            "booking": booking,
            "items": booking.items.all(),
            "core_discount": booking.base_total - booking.offer_total,
        }
        return render(request, self.template_name, context)
