from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Dashboard and main views
    path('', views.dashboard, name='dashboard'),
    path('permissions/', views.user_permissions, name='user_permissions'),
    
    # Approval workflows
    path('approvals/', views.approval_requests, name='approval_requests'),
    path('approvals/<int:pk>/', views.approval_detail, name='approval_detail'),
    path('approvals/<int:pk>/process/', views.process_approval, name='process_approval'),
    
    # Create approval requests
    path('create-expense-approval/', views.create_expense_approval, name='create_expense_approval'),
    path('create-advance-approval/', views.create_advance_approval, name='create_advance_approval'),
    
    # API endpoints
    path('api/approval-requests/', views.api_approval_requests, name='api_approval_requests'),
    path('api/approval-requests/<int:pk>/process/', views.api_process_approval, name='api_process_approval'),
]