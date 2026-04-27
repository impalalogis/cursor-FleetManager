from __future__ import annotations

from typing import Dict

from django.http import Http404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.utils.model_registry import (
    filter_valid_fields,
    get_model,
    get_model_versions,
    is_feature_enabled,
    iter_registered_models,
    model_to_metadata,
    serialise_queryset,
)


class BaseModelRegistryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_model(self, app_label: str, model_name: str):
        try:
            return get_model(app_label, model_name)
        except LookupError as exc:  # pragma: no cover - defensive
            raise Http404(str(exc)) from exc


class ModelListView(BaseModelRegistryView):
    """Return a catalogue of models exposed through the registry."""

    def get(self, request):
        results = []
        for model in iter_registered_models():
            meta = model._meta
            results.append({
                'app_label': meta.app_label,
                'model': meta.object_name,
                'model_name': meta.model_name,
                'verbose_name': meta.verbose_name,
                'verbose_name_plural': meta.verbose_name_plural,
                'fields': len(meta.fields),
                'relationships': len(meta.related_objects),
            })
        return Response({
            'count': len(results),
            'results': sorted(results, key=lambda item: (item['app_label'], item['model_name'])),
        })


class ModelMetadataView(BaseModelRegistryView):
    """Detailed metadata for a specific model."""

    def get(self, request, app_label: str, model_name: str):
        model = self._get_model(app_label, model_name)
        data = model_to_metadata(model)
        return Response(data)


class ModelExecuteView(BaseModelRegistryView):
    """Run a lightweight inference/query against the model dataset."""

    def post(self, request, app_label: str, model_name: str):
        if not is_feature_enabled('model_inference', True):
            return Response(
                {'detail': 'Model inference endpoint is currently disabled.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        model = self._get_model(app_label, model_name)

        payload: Dict = request.data or {}
        filters = payload.get('filters') or {}
        limit = payload.get('limit', 50)
        order_by = payload.get('order_by')

        if not isinstance(filters, dict):
            return Response({'detail': 'filters must be a dictionary'}, status=status.HTTP_400_BAD_REQUEST)

        valid_filters, invalid = filter_valid_fields(model, filters)
        if invalid:
            return Response(
                {'detail': 'Invalid filter keys supplied', 'invalid_filters': sorted(invalid)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = model.objects.filter(**valid_filters)
        if order_by:
            if isinstance(order_by, str):
                order_by = [order_by]
            valid_fields = {f.name for f in model._meta.get_fields()}
            invalid_order = [field for field in order_by if field.lstrip('-') not in valid_fields]
            if invalid_order:
                return Response(
                    {'detail': 'Invalid order_by fields', 'invalid_fields': invalid_order},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.order_by(*order_by)

        try:
            limit_int = int(limit)
        except (TypeError, ValueError):
            limit_int = 50

        results = serialise_queryset(model, qs, limit=limit_int)

        return Response({
            'count': len(results),
            'results': results,
        })


class ModelVersionView(BaseModelRegistryView):
    """Return migration/version history for the given model's app."""

    def get(self, request, app_label: str, model_name: str):
        # Ensure model exists and is exposed
        self._get_model(app_label, model_name)
        versions = get_model_versions(app_label)
        return Response({
            'app_label': app_label,
            'model': model_name,
            'versions': versions,
            'count': len(versions),
        })

