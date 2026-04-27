# """
# RBAC API URLs
# """
#
# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import (
#     RoleViewSet, PermissionViewSet, RolePermissionViewSet,
#     UserRoleViewSet, UserViewSet, ApprovalWorkflowViewSet,
#     ApprovalStepViewSet, ApprovalRequestViewSet, ApprovalActionViewSet
# )
#
# router = DefaultRouter()
# router.register(r'roles', RoleViewSet)
# router.register(r'permissions', PermissionViewSet)
# router.register(r'role-permissions', RolePermissionViewSet)
# router.register(r'user-roles', UserRoleViewSet)
# router.register(r'users', UserViewSet)
# router.register(r'approval-workflows', ApprovalWorkflowViewSet)
# router.register(r'approval-steps', ApprovalStepViewSet)
# router.register(r'approval-requests', ApprovalRequestViewSet)
# router.register(r'approval-actions', ApprovalActionViewSet)
#
# urlpatterns = [
#     path('', include(router.urls)),
# ]