"""
Entity API URLs
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BankingDetailViewSet,
    ChoiceViewSet,
    DriverDetail,
    DriverDocumentDetail,
    DriverDocumentListCreate,
    DriverFinancialSummary,
    DriverListCreate,
    LocationViewSet,
    OrganizationDetail,
    OrganizationDocumentDetail,
    OrganizationDocumentListCreate,
    OrganizationListCreate,
    RouteViewSet,
    VehicleDetail,
    VehicleDocumentDetail,
    VehicleDocumentListCreate,
    VehicleListCreate,
)

router = DefaultRouter()
router.register(r"choices", ChoiceViewSet, basename="entity-choice")
router.register(r"locations", LocationViewSet, basename="entity-location")
router.register(r"routes", RouteViewSet, basename="entity-route")
router.register(r"banking-details", BankingDetailViewSet, basename="entity-banking-detail")

urlpatterns = [
    path("organizations/", OrganizationListCreate.as_view(), name="organization-list-create"),
    path("organizations/<int:pk>/", OrganizationDetail.as_view(), name="organization-detail"),
    path("drivers/", DriverListCreate.as_view(), name="driver-list-create"),
    path("drivers/<int:pk>/", DriverDetail.as_view(), name="driver-detail"),
    path("drivers/<int:pk>/financial-summary/", DriverFinancialSummary.as_view(), name="driver-financial-summary"),
    path("vehicles/", VehicleListCreate.as_view(), name="vehicle-list-create"),
    path("vehicles/<uuid:pk>/", VehicleDetail.as_view(), name="vehicle-detail"),
    path("driver-documents/", DriverDocumentListCreate.as_view(), name="driver-document-list-create"),
    path("driver-documents/<int:pk>/", DriverDocumentDetail.as_view(), name="driver-document-detail"),
    path(
        "organization-documents/",
        OrganizationDocumentListCreate.as_view(),
        name="organization-document-list-create",
    ),
    path(
        "organization-documents/<int:pk>/",
        OrganizationDocumentDetail.as_view(),
        name="organization-document-detail",
    ),
    path("vehicle-documents/", VehicleDocumentListCreate.as_view(), name="vehicle-document-list-create"),
    path("vehicle-documents/<int:pk>/", VehicleDocumentDetail.as_view(), name="vehicle-document-detail"),
    path("", include(router.urls)),
]