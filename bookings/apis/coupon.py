from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from decimal import Decimal
from rest_framework.decorators import action
from rest_framework.response import Response
from bookings.models import Coupon, CouponRedemption
from bookings.serializers import CouponSerializer, CouponRedemptionSerializer

from drpathcare.pagination import StandardResultsSetPagination



class CouponRedemptionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CouponRedemption.objects.all().select_related("coupon", "user", "booking")
    serializer_class = CouponRedemptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        # normal users should see only their redemptions
        if not self.request.user.role:
            qs = qs.filter(user=self.request.user)
        else:
            user_param = self.request.query_params.get("user")
            if user_param:
                qs = qs.filter(user_id=user_param)
        return qs


class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all().order_by("-created_at")
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="validate")
    def validate_coupon(self, request):
        code = request.data.get("coupon_code")
        base_total = Decimal(request.data.get("base_total", "0.00"))
        user = request.user

        if not code:
            return Response({"error": "Coupon code is required"}, status=400)

        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            return Response({"valid": False, "message": "Invalid coupon"}, status=400)

        # ✅ Check active and date range
        if not coupon.is_valid_now():
            return Response({"valid": False, "message": "Coupon is not active or expired"}, status=400)

        # ✅ Global usage limit
        if coupon.usage_limit is not None and coupon.remaining_global_uses() == 0:
            return Response({"valid": False, "message": "Coupon usage limit reached"}, status=400)

        # ✅ Per-user usage limit
        user_uses = CouponRedemption.objects.filter(coupon=coupon, user=user).count()
        if coupon.per_user_limit is not None and user_uses >= coupon.per_user_limit:
            return Response({"valid": False, "message": "You have already used this coupon"}, status=400)

        # ✅ Calculate discount
        discount = Decimal("0.00")
        if coupon.discount_type == "percent":
            discount = (base_total * coupon.discount_value) / Decimal("100")
            if coupon.max_discount_amount:
                discount = min(discount, coupon.max_discount_amount)
        else:
            discount = coupon.discount_value

        final_amount = base_total - discount
        if final_amount < 0:
            final_amount = Decimal("0.00")

        return Response({
            "valid": True,
            "coupon_id": str(coupon.id),
            "discount": str(discount),
            "final_amount": str(final_amount),
            "message": "Coupon applied successfully",
        })
