"""
Main API URLs for Fleet Manager
"""

from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

app_name = 'api'

urlpatterns = [
    # API Documentation
    # path('schema/', SpectacularAPIView.as_view(), name='schema'),
    # path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    # path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),

    # API Version 1
    # path('v1/auth/', include('api.v1.auth.urls')),
    path('v1/entity/', include('api.v1.entity.urls')),
    path('v1/operations/', include('api.v1.operations.urls')),
    path('v1/financial/', include('api.v1.financial.urls')),
    path('v1/maintenance/', include('api.v1.maintenance.urls')),
    path('v1/models/', include('api.v1.model_registry.urls')),
    path('v1/admin/models/', include('api.v1.admin.models.urls')),
    # path('v1/rbac/', include('api.v1.rbac.urls')),
]