from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart, CartItem
from cart.serializers import (
    CartItemCreateSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
)
from cart.services import add_item_to_cart, get_or_create_cart


class CartDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        cart = get_or_create_cart(request.user)
        return Response(CartSerializer(cart).data)


class CartItemCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]
        try:
            item = add_item_to_cart(request.user, product, quantity)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)


class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CartItemUpdateSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "pk"

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user).select_related("product", "cart")

    def get_serializer_class(self):
        if self.request.method in ("GET", "DELETE"):
            return CartItemSerializer
        return CartItemUpdateSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(CartItemSerializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = CartItemUpdateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]
        if instance.product.stock_quantity < quantity:
            return Response({"detail": "Insufficient stock for requested quantity."}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(CartItemSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartClearView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request):
        cart = get_or_create_cart(request.user)
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
