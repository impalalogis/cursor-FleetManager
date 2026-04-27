"""Utilities for dynamic model registry APIs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from django.apps import apps
from django.conf import settings
from django.db import models

DEFAULT_EXCLUDED_APPS: Set[str] = {
    'users',
    'rbac',
}

DEFAULT_EXCLUDED_MODELS: Set[Tuple[str, str]] = {
    ('configuration', 'bankingdetail'),
    ('financial', 'banktransfer'),
}


def get_feature_flags() -> Dict[str, bool]:
    return getattr(settings, 'MODEL_API_FEATURE_FLAGS', {})


def is_feature_enabled(name: str, default: bool = True) -> bool:
    return get_feature_flags().get(name, default)


def get_excluded_apps() -> Set[str]:
    custom = getattr(settings, 'MODEL_API_EXCLUDED_APPS', None)
    if custom is None:
        return DEFAULT_EXCLUDED_APPS
    return set(custom)


def get_excluded_models() -> Set[Tuple[str, str]]:
    custom = getattr(settings, 'MODEL_API_EXCLUDED_MODELS', None)
    if custom is None:
        return DEFAULT_EXCLUDED_MODELS
    return {(
        item[0],
        item[1]
    ) for item in custom}


def normalise_model_name(name: str) -> str:
    return name.lower()


def is_model_allowed(model: models.Model) -> bool:
    app_label = model._meta.app_label
    model_name = normalise_model_name(model._meta.model_name)
    if app_label in get_excluded_apps():
        return False
    if (app_label, model_name) in get_excluded_models():
        return False
    return True


def iter_registered_models() -> Iterable[models.Model]:
    for model in apps.get_models():
        if model._meta.auto_created:
            continue
        if not is_model_allowed(model):
            continue
        app_config = model._meta.app_config
        base_dir = Path(settings.BASE_DIR)
        try:
            app_path = Path(app_config.path)
        except AttributeError:  # pragma: no cover - defensive
            continue
        if not str(app_path).startswith(str(base_dir)):
            continue
        yield model


def get_model(app_label: str, model_name: str) -> models.Model:
    model = apps.get_model(app_label, model_name)
    if model is None or not is_model_allowed(model):
        raise LookupError(f"Model {app_label}.{model_name} is not available via the model registry API")
    return model


def model_to_metadata(model: models.Model) -> Dict:
    opts = model._meta
    fields_meta: List[Dict] = []
    relations_meta: List[Dict] = []

    for field in opts.get_fields():
        info = {
            'name': field.name,
            'type': field.get_internal_type(),
            'verbose_name': getattr(field, 'verbose_name', field.name),
            'is_relation': field.is_relation,
            'many': field.many_to_many or field.one_to_many,
            'null': getattr(field, 'null', False),
            'editable': getattr(field, 'editable', False),
        }
        if field.is_relation:
            target = field.related_model
            info.update({
                'target_app': target._meta.app_label if target else None,
                'target_model': target._meta.model_name if target else None,
            })
            relations_meta.append(info)
        else:
            fields_meta.append(info)

    return {
        'app_label': opts.app_label,
        'model': opts.object_name,
        'model_name': opts.model_name,
        'verbose_name': opts.verbose_name,
        'verbose_name_plural': opts.verbose_name_plural,
        'db_table': opts.db_table,
        'fields': fields_meta,
        'relations': relations_meta,
    }


def serialise_queryset(model: models.Model, queryset: models.QuerySet, limit: int = 50) -> List[Dict]:
    limit = max(1, min(limit, 250))
    field_names = [f.name for f in model._meta.fields]
    records = list(queryset.values(*field_names)[:limit])
    return records


@dataclass
class MigrationInfo:
    name: str
    path: str
    modified_ts: float


def get_model_versions(app_label: str) -> List[Dict]:
    app_config = apps.get_app_config(app_label)
    migrations_dir = Path(app_config.path) / 'migrations'
    versions: List[Dict] = []
    if not migrations_dir.exists():
        return versions

    for file in sorted(migrations_dir.glob('[0-9][0-9][0-9][0-9]_*.py')):
        versions.append({
            'name': file.stem,
            'path': str(file.relative_to(app_config.path)),
            'modified_ts': file.stat().st_mtime,
        })
    return versions


def filter_valid_fields(model: models.Model, filters: Dict[str, object]) -> Tuple[Dict[str, object], Set[str]]:
    valid_field_names = {f.name for f in model._meta.get_fields() if not f.one_to_many and not f.many_to_many}
    valid_filters = {}
    invalid = set()
    for key, value in filters.items():
        if key in valid_field_names:
            valid_filters[key] = value
        else:
            invalid.add(key)
    return valid_filters, invalid

