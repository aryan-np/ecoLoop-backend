import uuid
import requests
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from ecoLoop.utils import api_response
from payments.models import Payment
from payments.serializers import (
    InitiatePaymentSerializer,
    VerifyPaymentSerializer,
    PaymentSerializer,
)


KHALTI_HEADERS = {
    "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
    "Content-Type": "application/json",
}


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        purchase_order_id = str(uuid.uuid4())

        payload = {
            "return_url": data["return_url"],
            "website_url": settings.WEBSITE_URL,
            "amount": data["amount"],
            "purchase_order_id": purchase_order_id,
            "purchase_order_name": data["purchase_order_name"],
        }

        if "customer_info" in data:
            payload["customer_info"] = data["customer_info"]

        try:
            response = requests.post(
                f"{settings.KHALTI_BASE_URL}epayment/initiate/",
                json=payload,
                headers=KHALTI_HEADERS,
                timeout=30,
            )
            khalti_data = response.json()
        except requests.exceptions.RequestException:
            return api_response(
                result=None,
                is_success=False,
                error_message=["Failed to connect to Khalti. Please try again."],
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if response.status_code != 200:
            return api_response(
                result=None,
                is_success=False,
                error_message=khalti_data,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.create(
            user=request.user,
            purchase_order_id=purchase_order_id,
            purchase_order_name=data["purchase_order_name"],
            amount=data["amount"],
            pidx=khalti_data["pidx"],
            status="Initiated",
            payment_url=khalti_data["payment_url"],
            expires_at=khalti_data.get("expires_at"),
            thread_id=data.get("thread_id"),
        )

        return api_response(
            result={
                "pidx": khalti_data["pidx"],
                "payment_url": khalti_data["payment_url"],
                "purchase_order_id": purchase_order_id,
                "expires_at": khalti_data.get("expires_at"),
                "expires_in": khalti_data.get("expires_in"),
            },
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        pidx = serializer.validated_data["pidx"]

        try:
            payment = Payment.objects.get(pidx=pidx, user=request.user)
        except Payment.DoesNotExist:
            return api_response(
                result=None,
                is_success=False,
                error_message=["Payment not found."],
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            response = requests.post(
                f"{settings.KHALTI_BASE_URL}epayment/lookup/",
                json={"pidx": pidx},
                headers=KHALTI_HEADERS,
                timeout=30,
            )
            khalti_data = response.json()
        except requests.exceptions.RequestException:
            return api_response(
                result=None,
                is_success=False,
                error_message=["Failed to connect to Khalti. Please try again."],
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if response.status_code not in (200, 400):
            return api_response(
                result=None,
                is_success=False,
                error_message=khalti_data,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        khalti_status = khalti_data.get("status")
        payment.status = khalti_status
        if khalti_data.get("transaction_id"):
            payment.transaction_id = khalti_data["transaction_id"]
        payment.save()

        is_success = khalti_status == "Completed"

        if is_success and payment.thread_id:
            thread = payment.thread
            offer = thread.offers.filter(status="accepted").order_by("-created_at").first()
            if offer:
                offer.is_paid = True
                offer.save(update_fields=["is_paid"])

                if thread.product:
                    thread.product.status = "sold"
                    thread.product.save(update_fields=["status"])

                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"thread_{thread.id}",
                    {
                        "type": "offer.event",
                        "offer_id": offer.id,
                        "amount": str(offer.amount),
                        "status": "accepted",
                        "proposed_by": str(offer.proposed_by_id),
                        "is_paid": True,
                    },
                )

        return api_response(
            result={
                "pidx": pidx,
                "status": khalti_status,
                "transaction_id": khalti_data.get("transaction_id"),
                "total_amount": khalti_data.get("total_amount"),
                "fee": khalti_data.get("fee"),
                "refunded": khalti_data.get("refunded"),
                "purchase_order_id": payment.purchase_order_id,
                "purchase_order_name": payment.purchase_order_name,
            },
            is_success=is_success,
            status_code=status.HTTP_200_OK,
        )


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related("user")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            result = {
                "count": getattr(self.paginator.page.paginator, "count", len(data)),
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "results": data,
            }
            return api_response(
                result=result,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        data = self.get_serializer(queryset, many=True).data
        return api_response(
            result=data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )
