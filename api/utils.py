"""
Shared API utilities for DRF endpoints.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            "error": True,
            "message": "An error occurred",
            "details": response.data,
            "status_code": response.status_code,
        }

        if response.status_code == 400:
            custom_response_data["message"] = "Bad request"
        elif response.status_code == 401:
            custom_response_data["message"] = "Authentication required"
        elif response.status_code == 403:
            custom_response_data["message"] = "Permission denied"
        elif response.status_code == 404:
            custom_response_data["message"] = "Resource not found"
        elif response.status_code == 500:
            custom_response_data["message"] = "Internal server error"

        response.data = custom_response_data
    else:
        if isinstance(exc, DjangoValidationError):
            response = Response(
                {
                    "error": True,
                    "message": "Validation error",
                    "details": exc.message_dict if hasattr(exc, "message_dict") else str(exc),
                    "status_code": 400,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif isinstance(exc, IntegrityError):
            response = Response(
                {
                    "error": True,
                    "message": "Data integrity error",
                    "details": str(exc),
                    "status_code": 400,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif isinstance(exc, Http404):
            response = Response(
                {
                    "error": True,
                    "message": "Resource not found",
                    "details": "Not found.",
                    "status_code": 404,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    if response and response.status_code >= 500:
        logger.error("API Error: %s", exc, exc_info=True)

    return response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Default pagination for all APIs.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Legacy permission helper kept for backward compatibility.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return hasattr(obj, "created_by") and obj.created_by == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Legacy permission helper kept for backward compatibility.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or request.user.is_superuser


class RBACPermission(permissions.BasePermission):
    """
    Legacy permission helper kept for backward compatibility.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        from utils.rbac import has_permission

        required_permission = getattr(view, "required_permission", None)
        if required_permission:
            return has_permission(request.user, required_permission)
        return True


def success_response(data=None, message="Success", status_code=200):
    response_data = {
        "error": False,
        "message": message,
        "status_code": status_code,
    }
    if data is not None:
        response_data["data"] = data
    return Response(response_data, status=status_code)


def error_response(message="Error occurred", details=None, status_code=400):
    response_data = {
        "error": True,
        "message": message,
        "status_code": status_code,
    }
    if details:
        response_data["details"] = details
    return Response(response_data, status=status_code)


class TimestampMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, "created_at") and instance.created_at:
            data["created_at_formatted"] = instance.created_at.strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(instance, "updated_at") and instance.updated_at:
            data["updated_at_formatted"] = instance.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        return data


class AuditMixin:
    def create(self, validated_data):
        if hasattr(self.context["request"], "user"):
            validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if hasattr(self.context["request"], "user"):
            validated_data["updated_by"] = self.context["request"].user
        return super().update(instance, validated_data)


class BulkModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet with reusable bulk operations.

    Bulk endpoints:
      - POST   /<resource>/bulk-create/
      - PATCH  /<resource>/bulk-update/
      - DELETE /<resource>/bulk-delete/
    """

    authentication_classes = []
    permission_classes = []

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request, *args, **kwargs):
        payload = request.data
        if not isinstance(payload, list):
            return Response({"detail": "Expected a list payload."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=payload, many=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            instances = serializer.save()
        out = self.get_serializer(instances, many=True)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["patch"], url_path="bulk-update")
    def bulk_update(self, request, *args, **kwargs):
        payload = request.data
        if not isinstance(payload, list):
            return Response({"detail": "Expected a list payload."}, status=status.HTTP_400_BAD_REQUEST)

        updated_rows = []
        with transaction.atomic():
            for row in payload:
                instance_id = row.get("id")
                if not instance_id:
                    return Response(
                        {"detail": "Each item must include 'id' for bulk update."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                instance = self.get_queryset().filter(pk=instance_id).first()
                if not instance:
                    return Response(
                        {"detail": f"Object with id={instance_id} not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                serializer = self.get_serializer(instance, data=row, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                updated_rows.append(serializer.data)

        return Response(updated_rows, status=status.HTTP_200_OK)

    @action(detail=False, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request, *args, **kwargs):
        ids = request.data.get("ids") if isinstance(request.data, dict) else None
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "Payload must include non-empty list 'ids'."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset().filter(pk__in=ids)
        deleted_count, _ = queryset.delete()
        return Response({"deleted": deleted_count}, status=status.HTTP_200_OK)
