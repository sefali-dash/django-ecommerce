from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser
from orders.models import Order
from orders.serializers import AdminOrderSerializer, AdminOrderStatusSerializer, OrderSerializer
from orders.services import CheckoutError, cancel_order, place_order_from_cart, update_order_status


class OrderCreateListView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")

    def create(self, request, *args, **kwargs):
        try:
            order = place_order_from_cart(request.user)
        except CheckoutError as exc:
            status_code = status.HTTP_400_BAD_REQUEST
            if exc.code == "insufficient_stock":
                status_code = status.HTTP_409_CONFLICT
            return Response({"detail": exc.message}, status=status_code)
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "pk"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class OrderCancelView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, user=request.user)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            order = cancel_order(order, by_user=True)
        except CheckoutError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data)


class AdminOrderListView(generics.ListAPIView):
    serializer_class = AdminOrderSerializer
    permission_classes = (IsAdminUser,)
    queryset = Order.objects.select_related("user").prefetch_related("items").all()


class AdminOrderStatusView(APIView):
    permission_classes = (IsAdminUser,)

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = AdminOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = update_order_status(order, serializer.validated_data["status"])
        except CheckoutError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AdminOrderSerializer(order).data)
