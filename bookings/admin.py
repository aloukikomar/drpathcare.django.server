from django.contrib import admin
from .models import Booking, BookingItem, BookingActionTracker, Cart, CartItem, Coupon, CouponRedemption

class BookingItemInline(admin.TabularInline):
    model = BookingItem
    extra = 0
    readonly_fields = ("base_price", "offer_price", "created_at", "updated_at")
    fields = ("patient", "lab_test", "profile", "package", "base_price", "offer_price", "created_at")

class BookingActionInline(admin.TabularInline):
    model = BookingActionTracker
    extra = 0
    readonly_fields = ("user", "action", "notes", "created_at")

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "payment_status", "final_amount", "created_at")
    search_fields = ("id", "user__email")
    list_filter = ("status", "payment_status", "created_at")
    inlines = [BookingItemInline, BookingActionInline]

@admin.register(BookingItem)
class BookingItemAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "patient", "lab_test", "profile", "package", "base_price", "offer_price")
    search_fields = ("booking__id", "patient__first_name", "lab_test__name")

@admin.register(BookingActionTracker)
class BookingActionAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "user", "action", "created_at")
    search_fields = ("booking__id", "user__email", "action")
    list_filter = ("action",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "updated_at")
    search_fields = ("user__email",)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "patient", "lab_test", "profile", "package", "quantity", "base_price", "offer_price")
    search_fields = ("cart__id", "patient__first_name", "lab_test__name")

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "active", "valid_from", "valid_to")
    search_fields = ("code",)
    list_filter = ("discount_type", "active")

@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "user", "booking", "used_at")
    search_fields = ("coupon__code", "user__email", "booking__id")
