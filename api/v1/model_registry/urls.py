from django.urls import path

from .views import (
    ModelExecuteView,
    ModelListView,
    ModelMetadataView,
    ModelVersionView,
)

app_name = 'model_registry'

urlpatterns = [
    path('', ModelListView.as_view(), name='model-list'),
    path('<str:app_label>/<str:model_name>/', ModelMetadataView.as_view(), name='model-detail'),
    path('<str:app_label>/<str:model_name>/execute/', ModelExecuteView.as_view(), name='model-execute'),
    path('<str:app_label>/<str:model_name>/versions/', ModelVersionView.as_view(), name='model-versions'),
]

