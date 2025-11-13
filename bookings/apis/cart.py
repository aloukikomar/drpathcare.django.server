from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from bookings.models import Cart, CartItem
from bookings.serializers import CartSerializer, CartItemSerializer
from lab.models import LabTest, Profile, Package


class CartViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        product_type = request.data.get("product_type")
        product_id = request.data.get("product_id")

        if not product_type or not product_id:
            return Response(
                {"error": "Both 'product_type' and 'product_id' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart, _ = Cart.objects.get_or_create(user=user)

        model_map = {
            "LabTest": LabTest,
            "Profile": Profile,
            "Package": Package,
        }

        model = model_map.get(product_type)
        if not model:
            return Response(
                {"error": f"Invalid product_type: {product_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = model.objects.get(id=product_id)
        except model.DoesNotExist:
            return Response(
                {"error": f"{product_type} with id {product_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ✅ check if already exists (using new fields)
        existing_item = CartItem.objects.filter(
            cart=cart,
            product_type=product_type,
            product_id=product_id,
        ).first()

        if existing_item:
            return Response({"detail": "Item already in cart."}, status=status.HTTP_200_OK)

        # ✅ create new unified CartItem
        CartItem.objects.create(
            cart=cart,
            product_type=product_type,
            product_id=product.id,
            product_name=product.name,
            base_price=product.price,
            offer_price=getattr(product, "offer_price", None),
        )

        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def clear(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response({"detail": "Cart cleared successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def items(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.all()
        serializer = CartItemSerializer(items, many=True, context={"request": request})
        return Response(serializer.data)
