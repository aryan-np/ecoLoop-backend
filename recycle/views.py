from django.shortcuts import render
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from recycle.models import ScrapCategory, ScrapRequest, ScrapOffer
from recycle.serializers import (
    ScrapCategorySerializer,
    ScrapRequestSerializer,
    RecyclerScrapRequestSerializer,
    ScrapOfferSerializer,
    RecyclerAcceptedScrapRequestSerializer,
)
from recycle.filters import ScrapRequestFilter
from ecoLoop.utils import api_response
from accounts.permissions import IsRecycler

# Create your views here.


class ScrapCategoryViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]
    queryset = ScrapCategory.objects.all()
    serializer_class = ScrapCategorySerializer

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


class ScrapRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ScrapRequestSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filterset_class = ScrapRequestFilter

    def get_queryset(self):
        # Users can only see their own scrap requests
        return (
            ScrapRequest.objects.filter(user=self.request.user)
            .prefetch_related("images")
            .select_related("category")
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


class RecyclerScrapRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Recycler users to view all pending scrap requests.
    Recyclers can list and retrieve pending scrap requests but cannot modify them.
    Supports filtering by category, condition, and weight range.
    """

    permission_classes = [IsAuthenticated, IsRecycler]
    serializer_class = RecyclerScrapRequestSerializer
    filterset_class = ScrapRequestFilter

    def get_queryset(self):
        # Recycler can see all pending scrap requests
        return (
            ScrapRequest.objects.filter(status="Pending")
            .prefetch_related("images")
            .select_related("category", "user")
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
        Recycler accepts a scrap request and creates an offer.
        This changes the request status to 'accepted' and creates a scrap offer.

        """

        # Get the scrap request without status filter to check if it exists
        try:
            scrap_request = ScrapRequest.objects.get(id=pk)
        except ScrapRequest.DoesNotExist:
            return api_response(
                result=None,
                is_success=False,
                error_message="Scrap request not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Check if request is still pending
        if scrap_request.status != "Pending":
            return api_response(
                result=None,
                is_success=False,
                error_message=f"Cannot accept request with status: {scrap_request.status}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Create the offer
        offer_serializer = ScrapOfferSerializer(data=request.data)
        if not offer_serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=offer_serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Update request status
        scrap_request.status = "accepted"
        scrap_request.save()

        # Save the offer
        offer = offer_serializer.save(
            recycler=request.user, scrap_request=scrap_request
        )

        return api_response(
            result={
                "message": "Scrap request accepted successfully",
                "offer": ScrapOfferSerializer(offer).data,
                "request": RecyclerScrapRequestSerializer(scrap_request).data,
            },
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )


class RecyclerAcceptedScrapRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Recycler users to view accepted scrap requests.
    Recyclers can list and retrieve accepted scrap requests with offer details.
    Supports filtering by category, condition, and weight range.
    """

    permission_classes = [IsAuthenticated, IsRecycler]
    serializer_class = RecyclerAcceptedScrapRequestSerializer
    filterset_class = ScrapRequestFilter

    def get_queryset(self):
        # Recycler can see all accepted scrap requests
        return (
            ScrapRequest.objects.filter(status="accepted")
            .prefetch_related("images", "recycler_offers")
            .select_related("category", "user")
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


class RecyclerAcceptedScrapRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Recycler users to view accepted scrap requests.
    Recyclers can list and retrieve accepted scrap requests with offer details.
    Supports filtering by category, condition, and weight range.
    """

    permission_classes = [IsAuthenticated, IsRecycler]
    serializer_class = RecyclerAcceptedScrapRequestSerializer
    filterset_class = ScrapRequestFilter

    def get_queryset(self):
        # Recycler can see all accepted scrap requests
        return (
            ScrapRequest.objects.filter(status="accepted")
            .prefetch_related("images", "recycler_offers")
            .select_related("category", "user")
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
