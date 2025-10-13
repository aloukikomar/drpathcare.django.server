# bookings/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction

from decimal import Decimal, ROUND_HALF_UP

from bookings.models import Cart, CartItem, Coupon, CouponRedemption, Booking, BookingItem, BookingActionTracker
from bookings.serializers import CartSerializer, CartItemSerializer, BookingSerializer

# Pagination import if you use one
from drpathcare.pagination import StandardResultsSetPagination


class CartViewSet(viewsets.ModelViewSet):
    """
    Standard CRUD for carts. Users typically create one cart per user; staff can create/manage others.
    """
    queryset = Cart.objects.all().prefetch_related("items")
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            # normal users only see their carts
            qs = qs.filter(user=self.request.user)
        else:
            user_param = self.request.query_params.get("user")
            if user_param:
                qs = qs.filter(user_id=user_param)
        return qs

    @action(detail=True, methods=["post"])
    def add_item(self, request, pk=None):
        """
        POST data: patient, lab_test OR profile OR package, quantity(optional), base_price(optional), offer_price(optional)
        """
        cart = self.get_object()
        data = request.data.copy()
        data["cart"] = str(cart.id)
        serializer = CartItemSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        # permission: ensure user owns cart unless staff
        if not request.user.is_staff and cart.user != request.user:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        item = serializer.save()
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        """
        Convert cart into a Booking and BookingItems.
        POST body optional:
          - address (id) or address fields in case user passes address
          - coupon_code (string) optional
          - scheduled_date, scheduled_time (optional)
        """
        cart = self.get_object()
        if not cart.items.exists():
            return Response({"detail": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.is_staff and cart.user != request.user:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        coupon_code = request.data.get("coupon_code")
        address_id = request.data.get("address")
        scheduled_date = request.data.get("scheduled_date")
        scheduled_time = request.data.get("scheduled_time")
        remarks = request.data.get("remarks")

        # Validate coupon if provided
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code)
            except Coupon.DoesNotExist:
                return Response({"detail": "Invalid coupon code"}, status=status.HTTP_400_BAD_REQUEST)
            if not coupon.is_valid_now():
                return Response({"detail": "Coupon not valid at this time"}, status=status.HTTP_400_BAD_REQUEST)
            # check usage limits
            if coupon.usage_limit is not None and coupon.redemptions.count() >= coupon.usage_limit:
                return Response({"detail": "Coupon usage limit reached"}, status=status.HTTP_400_BAD_REQUEST)
            if coupon.per_user_limit is not None:
                user_uses = CouponRedemption.objects.filter(coupon=coupon, user=cart.user).count()
                if user_uses >= coupon.per_user_limit:
                    return Response({"detail": "You have reached per-user limit for this coupon"}, status=status.HTTP_400_BAD_REQUEST)

        # Build booking inside a transaction
        with transaction.atomic():
            # create booking
            booking = Booking.objects.create(
                user=cart.user,
                address_id=address_id if address_id else None,
                scheduled_date=scheduled_date if scheduled_date else None,
                scheduled_time=scheduled_time if scheduled_time else None,
                remarks=remarks or ""
            )

            created_items = []
            for ci in cart.items.all():
                # create BookingItem snapshot per cart item
                bi = BookingItem.objects.create(
                    booking=booking,
                    patient=ci.patient,
                    lab_test=ci.lab_test,
                    profile=ci.profile,
                    package=ci.package,
                    base_price=(ci.base_price or Decimal("0.00")) * Decimal(ci.quantity),
                    offer_price=(ci.offer_price if ci.offer_price is not None else ci.base_price) * Decimal(ci.quantity)
                )
                created_items.append(bi)

            # recalc totals
            booking.recalc_totals()

            # apply coupon if present
            discount_amount = Decimal("0.00")
            if coupon:
                # calculate discount from booking.final_amount (which uses offer prices)
                if coupon.discount_type == "percent":
                    pct = (coupon.discount_value or Decimal("0")) / Decimal(100)
                    raw_discount = (booking.final_amount * pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if coupon.max_discount_amount:
                        discount_amount = min(raw_discount, coupon.max_discount_amount)
                    else:
                        discount_amount = raw_discount
                else:  # flat
                    discount_amount = coupon.discount_value or Decimal("0.00")
                # ensure non-negative, not exceed final_amount
                discount_amount = max(Decimal("0.00"), min(discount_amount, booking.final_amount))

                # persist coupon to booking
                booking.coupon = coupon
                booking.discount_amount = discount_amount
                booking.final_amount = (booking.final_amount - discount_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                booking.total_savings = (booking.base_total - booking.final_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                booking.save(update_fields=["coupon", "discount_amount", "final_amount", "total_savings", "updated_at"])

                # create redemption record
                CouponRedemption.objects.create(coupon=coupon, user=cart.user, booking=booking)

            # log booking creation
            BookingActionTracker.objects.create(
                booking=booking,
                user=request.user,
                action="create",
                notes=f"Created by checkout from cart {cart.id}"
            )

            # Optionally clear cart items (and cart)
            cart.items.all().delete()
            cart.delete()

            serializer = BookingSerializer(booking)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

