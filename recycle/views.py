from django.shortcuts import render
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.response import Response
from recycle.models import ScrapCategory, ScrapRequest
from recycle.serializers import ScrapCategorySerializer, ScrapRequestSerializer

# Create your views here.


class ScrapCategoryViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]
    queryset = ScrapCategory.objects.all()
    serializer_class = ScrapCategorySerializer


class ScrapRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ScrapRequestSerializer

    def get_queryset(self):
        # Users can only see their own scrap requests
        return ScrapRequest.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set the user to the authenticated user
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
