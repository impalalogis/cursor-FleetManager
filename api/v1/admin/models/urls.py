from django.urls import path

from .views import ModelAdminCollectionView, ModelAdminDetailView

app_name = 'model_admin'

urlpatterns = [
    path('<str:app_label>/<str:model_name>/', ModelAdminCollectionView.as_view(), name='collection'),
    path('<str:app_label>/<str:model_name>/<str:pk>/', ModelAdminDetailView.as_view(), name='detail'),
]

