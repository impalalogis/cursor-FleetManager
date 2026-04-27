from __future__ import annotations

import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.forms.models import model_to_dict
from django.http import Http404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.utils.model_registry import (
    filter_valid_fields,
    get_model,
    is_feature_enabled,
    serialise_queryset,
)


LOGGER = logging.getLogger('model_admin_api')


class BaseModelAdminView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def _get_model(self, app_label: str, model_name: str):
        try:
            return get_model(app_label, model_name)
        except LookupError as exc:  # pragma: no cover - defensive
            raise Http404(str(exc)) from exc

    def _serialise(self, instance):
        return model_to_dict(instance)

    def _log(self, request, action: str, app_label: str, model_name: str, payload=None, pk=None):
        LOGGER.info(
            "model_admin_action",
            extra={
                'user': getattr(request.user, 'username', 'anonymous'),
                'action': action,
                'app_label': app_label,
                'model': model_name,
                'pk': pk,
                'payload': payload or {},
                'path': request.path,
            }
        )

    def _ensure_feature(self, flag: str):
        if not is_feature_enabled(flag, True):
            raise PermissionDenied(detail=f'Feature flag "{flag}" is disabled.')


class ModelAdminCollectionView(BaseModelAdminView):
    """List or create model instances dynamically."""

    def get(self, request, app_label: str, model_name: str):
        model = self._get_model(app_label, model_name)
        filters = request.query_params.dict()
        limit = int(filters.pop('limit', 50) or 50)
        valid_filters, invalid = filter_valid_fields(model, filters)
        if invalid:
            return Response(
                {'detail': 'Invalid query parameters', 'invalid_filters': sorted(invalid)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = model.objects.filter(**valid_filters)
        results = serialise_queryset(model, qs, limit=limit)
        return Response({'count': len(results), 'results': results})

    def post(self, request, app_label: str, model_name: str):
        self._ensure_feature('model_admin_write')
        model = self._get_model(app_label, model_name)
        payload = request.data or {}

        instance = model()
        for field, value in payload.items():
            if hasattr(instance, field):
                setattr(instance, field, value)

        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict)

        instance.save()
        self._log(request, 'create', app_label, model_name, payload=payload, pk=instance.pk)
        return Response(self._serialise(instance), status=status.HTTP_201_CREATED)


class ModelAdminDetailView(BaseModelAdminView):
    """Retrieve, update, or delete a specific instance."""

    def get_object(self, model, pk):
        try:
            return model.objects.get(pk=pk)
        except ObjectDoesNotExist as exc:
            raise Http404(str(exc))

    def get(self, request, app_label: str, model_name: str, pk: str):
        model = self._get_model(app_label, model_name)
        instance = self.get_object(model, pk)
        return Response(self._serialise(instance))

    def patch(self, request, app_label: str, model_name: str, pk: str):
        self._ensure_feature('model_admin_write')
        model = self._get_model(app_label, model_name)
        instance = self.get_object(model, pk)
        payload = request.data or {}

        for field, value in payload.items():
            if hasattr(instance, field):
                setattr(instance, field, value)

        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict)

        instance.save()
        self._log(request, 'update', app_label, model_name, payload=payload, pk=pk)
        return Response(self._serialise(instance))

    def put(self, request, app_label: str, model_name: str, pk: str):
        return self.patch(request, app_label, model_name, pk)

    def delete(self, request, app_label: str, model_name: str, pk: str):
        self._ensure_feature('model_admin_delete')
        model = self._get_model(app_label, model_name)
        instance = self.get_object(model, pk)
        instance.delete()
        self._log(request, 'delete', app_label, model_name, pk=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

