from django.shortcuts import render
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import DonationCategory, DonationCondition, DonationRequest, NGOOffer
from .serializers import (
    DonationCategorySerializer,
    DonationConditionSerializer,
    DonationRequestSerializer,
    NGODonationRequestSerializer,
    NGOOfferSerializer,
    NGOAcceptedDonationRequestSerializer,
)
from ecoLoop.utils import api_response
from accounts.permissions import IsNGO


# Create your views here.


class DonationCategoryViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]
    queryset = DonationCategory.objects.all()
    serializer_class = DonationCategorySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            result=serializer.data,
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


class DonationConditionViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]
    queryset = DonationCondition.objects.all()
    serializer_class = DonationConditionSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            result=serializer.data,
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


class DonationRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DonationRequestSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        # Users can only see their own donation requests
        return DonationRequest.objects.filter(user=self.request.user).prefetch_related(
            "images"
        )

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Set the user to the authenticated user
        serializer.save(user=request.user)

        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)

        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        self.perform_update(serializer)

        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        self.perform_update(serializer)

        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        return api_response(
            result={"message": "Deleted."},
            is_success=True,
            status_code=status.HTTP_204_NO_CONTENT,
        )


class NGODonationRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for NGO users to view all pending donation requests.
    NGO can list and retrieve pending donation requests but cannot modify them.
    """

    permission_classes = [IsAuthenticated, IsNGO]
    serializer_class = NGODonationRequestSerializer

    def get_queryset(self):
        # NGO can see all pending donation requests
        return (
            DonationRequest.objects.filter(status="pending")
            .prefetch_related("images")
            .select_related("user", "category", "condition")
        )

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

    @action(detail=True, methods=["post"], url_path="accept")
    def accept_request(self, request, pk=None):
        """
        NGO accepts a donation request and creates an offer.
        This changes the request status to 'accepted' and creates an NGO offer.
        """
        # Get the donation request without status filter to check if it exists
        try:
            donation_request = DonationRequest.objects.get(id=pk)
        except DonationRequest.DoesNotExist:
            return api_response(
                result=None,
                is_success=False,
                error_message="Donation request not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Check if request is still pending
        if donation_request.status != "pending":
            return api_response(
                result=None,
                is_success=False,
                error_message=f"Cannot accept request with status: {donation_request.status}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Create the offer
        offer_serializer = NGOOfferSerializer(data=request.data)
        if not offer_serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=offer_serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Update request status
        donation_request.status = "accepted"
        donation_request.save()

        # Save the offer
        offer = offer_serializer.save(
            ngo=request.user, donation_request=donation_request
        )

        return api_response(
            result={
                "message": "Donation request accepted successfully",
                "offer": NGOOfferSerializer(offer).data,
                "request": NGODonationRequestSerializer(donation_request).data,
            },
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )


class NGOAcceptedDonationRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for NGO users to view accepted donation requests.
    NGO can list and retrieve accepted donation requests with offer details.
    """

    permission_classes = [IsAuthenticated, IsNGO]
    serializer_class = NGOAcceptedDonationRequestSerializer

    def get_queryset(self):
        # NGO can see all accepted donation requests
        return (
            DonationRequest.objects.filter(status="accepted")
            .prefetch_related("images", "ngo_offers")
            .select_related("user", "category", "condition")
        )

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
