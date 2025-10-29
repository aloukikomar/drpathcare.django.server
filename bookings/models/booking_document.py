from django.conf import settings 
from django.db import models
from bookings.models.booking import Booking

class BookingDocument(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file_url = models.URLField(max_length=1024)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    doc_type = models.CharField(max_length=50, blank=True, null=True)  # e.g. 'cash_receipt', 'lab_report', etc.

    def __str__(self):
        return f"{self.name} ({self.booking_id})"
