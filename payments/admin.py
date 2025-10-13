# payments/admin.py
from django.contrib import admin
from .models import BookingPayment

@admin.register(BookingPayment)
class BookingPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "amount", "status", "method", "created_at")
    list_filter = ("status", "method", "created_at")
    search_fields = ("transaction_id", "booking__id")
