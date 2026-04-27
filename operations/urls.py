from django.urls import path
from .views import expense_by_autocomplete

urlpatterns = [
    path(
        "expense-by-autocomplete/",
        expense_by_autocomplete,
        name="expense_by_autocomplete"
    ),
]
