"""
API Utilities for Fleet Manager
Contains custom exception handlers, permissions, and common mixins
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Custom error handling
    if response is not None:
        custom_response_data = {
            'error': True,
            'message': 'An error occurred',
            'details': response.data,
            'status_code': response.status_code
        }

        # Handle specific error types
        if response.status_code == 400:
            custom_response_data['message'] = 'Bad request'
        elif response.status_code == 401:
            custom_response_data['message'] = 'Authentication required'
        elif response.status_code == 403:
            custom_response_data['message'] = 'Permission denied'
        elif response.status_code == 404:
            custom_response_data['message'] = 'Resource not found'
        elif response.status_code == 500:
            custom_response_data['message'] = 'Internal server error'

        response.data = custom_response_data
    else:
        # Handle Django validation errors
        if isinstance(exc, DjangoValidationError):
            custom_response_data = {
                'error': True,
                'message': 'Validation error',
                'details': exc.message_dict if hasattr(exc, 'message_dict') else str(exc),
                'status_code': 400
            }
            response = Response(custom_response_data, status=status.HTTP_400_BAD_REQUEST)

        # Handle integrity errors (duplicate keys, etc.)
        elif isinstance(exc, IntegrityError):
            custom_response_data = {
                'error': True,
                'message': 'Data integrity error',
                'details': str(exc),
                'status_code': 400
            }
            response = Response(custom_response_data, status=status.HTTP_400_BAD_REQUEST)

    # Log the error
    if response and response.status_code >= 500:
        logger.error(f"API Error: {exc}", exc_info=True)

    return response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class with configurable page size
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object
        return hasattr(obj, 'created_by') and obj.created_by == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or request.user.is_superuser


class RBACPermission(permissions.BasePermission):
    """
    Custom permission class that integrates with the RBAC system
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Import here to avoid circular imports
        from utils.rbac import has_permission

        # Get the required permission from the view
        required_permission = getattr(view, 'required_permission', None)
        if required_permission:
            return has_permission(request.user, required_permission)

        return True


def success_response(data=None, message="Success", status_code=200):
    """
    Standardized success response format
    """
    response_data = {
        'error': False,
        'message': message,
        'status_code': status_code
    }

    if data is not None:
        response_data['data'] = data

    return Response(response_data, status=status_code)


def error_response(message="Error occurred", details=None, status_code=400):
    """
    Standardized error response format
    """
    response_data = {
        'error': True,
        'message': message,
        'status_code': status_code
    }

    if details:
        response_data['details'] = details

    return Response(response_data, status=status_code)


class TimestampMixin:
    """
    Mixin to add timestamp fields to serializers
    """
    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Add formatted timestamps
        if hasattr(instance, 'created_at') and instance.created_at:
            data['created_at_formatted'] = instance.created_at.strftime('%Y-%m-%d %H:%M:%S')

        if hasattr(instance, 'updated_at') and instance.updated_at:
            data['updated_at_formatted'] = instance.updated_at.strftime('%Y-%m-%d %H:%M:%S')

        return data


class AuditMixin:
    """
    Mixin to handle audit fields in serializers
    """
    def create(self, validated_data):
        # Set created_by to current user
        if hasattr(self.context['request'], 'user'):
            validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Set updated_by to current user
        if hasattr(self.context['request'], 'user'):
            validated_data['updated_by'] = self.context['request'].user
        return super().update(instance, validated_data)