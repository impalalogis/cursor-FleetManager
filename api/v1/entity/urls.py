"""
Entity API URLs
"""

from django.urls import path
from .views import (
    OrganizationListCreate, OrganizationDetail,
    DriverListCreate, DriverDetail,
    VehicleListCreate, VehicleDetail
)



urlpatterns = [

    path("organizations/", OrganizationListCreate.as_view(), name="organization-list-create"),
    path("organizations/<int:pk>/", OrganizationDetail.as_view(), name="organization-detail"),

    path("drivers/", DriverListCreate.as_view(), name="driver-list-create"),
    path("drivers/<int:pk>/", DriverDetail.as_view(), name="driver-detail"),

    path("vehicles/", VehicleListCreate.as_view(), name="vehicle-list-create"),
    path("vehicles/<uuid:pk>/", VehicleDetail.as_view(), name="vehicle-detail"),

]