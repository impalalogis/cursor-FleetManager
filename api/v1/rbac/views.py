# """
# RBAC Views for Fleet Manager API
# Comprehensive viewsets matching admin panel functionality
# """
#
# from rest_framework import viewsets, permissions, filters, status
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from django_filters.rest_framework import DjangoFilterBackend
# from drf_spectacular.utils import extend_schema, OpenApiParameter
# from django.db.models import Q, Count
# from django.utils import timezone
#
# from rbac.models import (
#     Role, Permission, RolePermission, UserRole,
#     ApprovalWorkflow, ApprovalStep, ApprovalRequest, ApprovalAction
# )
# from security.models import CustomUser
# from api.utils import IsOwnerOrReadOnly, success_response, error_response
# from .serializers import (
#     RoleSerializer, PermissionSerializer, RolePermissionSerializer,
#     UserRoleSerializer, ApprovalWorkflowSerializer, ApprovalStepSerializer,
#     ApprovalRequestSerializer, ApprovalActionSerializer, UserSerializer
# )
#
#
# class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
#     """ViewSet for Permission model (read-only)"""
#     queryset = Permission.objects
#     serializer_class = PermissionSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['module', 'is_active']
#     search_fields = ['name', 'codename', 'description']
#
#     @action(detail=False, methods=['get'])
#     def by_module(self, request):
#         """Get permissions grouped by module"""
#         module = request.query_params.get('module')
#         if not module:
#             return Response(error_response('Module parameter is required'), status=400)
#
#         permissions = self.queryset.filter(module=module)
#         serializer = self.get_serializer(permissions, many=True)
#         return Response(success_response(serializer.data))
#
#
# class RoleViewSet(viewsets.ModelViewSet):
#     """ViewSet for Role model"""
#     queryset = Role.objects.prefetch_related('role_permissions__permission', 'user_roles').all()
#     serializer_class = RoleSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_fields = ['is_active', 'is_system_role']
#     search_fields = ['name', 'description']
#     ordering_fields = ['name', 'created_at']
#     ordering = ['name']
#
#     @action(detail=True, methods=['get'])
#     def permissions(self, request, pk=None):
#         """Get permissions for a specific role"""
#         role = self.get_object()
#         role_permissions = role.role_permissions.filter(is_active=True).select_related('permission')
#         serializer = RolePermissionSerializer(role_permissions, many=True)
#         return Response(success_response(serializer.data))
#
#     @action(detail=True, methods=['post'])
#     def assign_permission(self, request, pk=None):
#         """Assign permission to role"""
#         role = self.get_object()
#         permission_id = request.data.get('permission_id')
#
#         if not permission_id:
#             return Response(error_response('Permission ID is required'), status=400)
#
#         try:
#             permission = Permission.objects.get(id=permission_id)
#             role_permission, created = RolePermission.objects.get_or_create(
#                 role=role,
#                 permission=permission,
#                 defaults={
#                     'can_create': request.data.get('can_create', False),
#                     'can_read': request.data.get('can_read', True),
#                     'can_update': request.data.get('can_update', False),
#                     'can_delete': request.data.get('can_delete', False),
#                     'can_approve': request.data.get('can_approve', False),
#                 }
#             )
#
#             if not created:
#                 # Update existing permission
#                 role_permission.can_create = request.data.get('can_create', role_permission.can_create)
#                 role_permission.can_read = request.data.get('can_read', role_permission.can_read)
#                 role_permission.can_update = request.data.get('can_update', role_permission.can_update)
#                 role_permission.can_delete = request.data.get('can_delete', role_permission.can_delete)
#                 role_permission.can_approve = request.data.get('can_approve', role_permission.can_approve)
#                 role_permission.is_active = True
#                 role_permission.save()
#
#             serializer = RolePermissionSerializer(role_permission)
#             return Response(success_response(serializer.data))
#
#         except Permission.DoesNotExist:
#             return Response(error_response('Permission not found'), status=404)
#
#     @action(detail=True, methods=['delete'])
#     def remove_permission(self, request, pk=None):
#         """Remove permission from role"""
#         role = self.get_object()
#         permission_id = request.data.get('permission_id')
#
#         if not permission_id:
#             return Response(error_response('Permission ID is required'), status=400)
#
#         try:
#             role_permission = RolePermission.objects.get(role=role, permission_id=permission_id)
#             role_permission.is_active = False
#             role_permission.save()
#
#             return Response(success_response({'message': 'Permission removed successfully'}))
#
#         except RolePermission.DoesNotExist:
#             return Response(error_response('Role permission not found'), status=404)
#
#     @action(detail=True, methods=['get'])
#     def users(self, request, pk=None):
#         """Get users with this role"""
#         role = self.get_object()
#         user_roles = role.user_roles.filter(is_active=True).select_related('user')
#         serializer = UserRoleSerializer(user_roles, many=True)
#         return Response(success_response(serializer.data))
#
#
# class RolePermissionViewSet(viewsets.ModelViewSet):
#     """ViewSet for RolePermission model"""
#     queryset = RolePermission.objects.select_related('role', 'permission').all()
#     serializer_class = RolePermissionSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['role', 'permission', 'is_active']
#     search_fields = ['role__name', 'permission__name']
#
#
# class UserRoleViewSet(viewsets.ModelViewSet):
#     """ViewSet for UserRole model"""
#     queryset = UserRole.objects.select_related('user', 'role').all()
#     serializer_class = UserRoleSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_fields = ['user', 'role', 'is_active']
#     search_fields = ['user__username', 'user__email', 'role__name']
#     ordering_fields = ['assigned_date']
#     ordering = ['-assigned_date']
#
#     @action(detail=False, methods=['post'])
#     def assign_role(self, request):
#         """Assign role to user"""
#         user_id = request.data.get('user_id')
#         role_id = request.data.get('role_id')
#
#         if not user_id or not role_id:
#             return Response(error_response('User ID and Role ID are required'), status=400)
#
#         try:
#             user = CustomUser.objects.get(id=user_id)
#             role = Role.objects.get(id=role_id)
#
#             user_role, created = UserRole.objects.get_or_create(
#                 user=user,
#                 role=role,
#                 defaults={'is_active': True}
#             )
#
#             if not created:
#                 user_role.is_active = True
#                 user_role.save()
#
#             serializer = self.get_serializer(user_role)
#             return Response(success_response(serializer.data))
#
#         except (CustomUser.DoesNotExist, Role.DoesNotExist) as e:
#             return Response(error_response(str(e)), status=404)
#
#     @action(detail=True, methods=['post'])
#     def deactivate(self, request, pk=None):
#         """Deactivate user role"""
#         user_role = self.get_object()
#         user_role.is_active = False
#         user_role.save()
#
#         serializer = self.get_serializer(user_role)
#         return Response(success_response(serializer.data))
#
#
# class UserViewSet(viewsets.ModelViewSet):
#     """ViewSet for CustomUser model"""
#     queryset = CustomUser.objects.prefetch_related('user_roles__role').all()
#     serializer_class = UserSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_fields = ['is_active', 'is_staff', 'is_superuser']
#     search_fields = ['username', 'email', 'first_name', 'last_name']
#     ordering_fields = ['username', 'email', 'date_joined', 'last_login']
#     ordering = ['username']
#
#     @action(detail=True, methods=['get'])
#     def roles(self, request, pk=None):
#         """Get user's roles"""
#         user = self.get_object()
#         user_roles = user.user_roles.filter(is_active=True).select_related('role')
#         serializer = UserRoleSerializer(user_roles, many=True)
#         return Response(success_response(serializer.data))
#
#     @action(detail=True, methods=['get'])
#     def permissions(self, request, pk=None):
#         """Get user's effective permissions"""
#         user = self.get_object()
#         user_roles = user.user_roles.filter(is_active=True).select_related('role')
#
#         permissions = []
#         for user_role in user_roles:
#             role_permissions = user_role.role.role_permissions.filter(is_active=True).select_related('permission')
#             for rp in role_permissions:
#                 permissions.append({
#                     'permission_id': rp.permission.id,
#                     'permission_name': rp.permission.name,
#                     'permission_codename': rp.permission.codename,
#                     'module': rp.permission.module,
#                     'role_name': user_role.role.name,
#                     'can_create': rp.can_create,
#                     'can_read': rp.can_read,
#                     'can_update': rp.can_update,
#                     'can_delete': rp.can_delete,
#                     'can_approve': rp.can_approve,
#                 })
#
#         return Response(success_response(permissions))
#
#
# class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
#     """ViewSet for ApprovalWorkflow model"""
#     queryset = ApprovalWorkflow.objects.prefetch_related('steps').all()
#     serializer_class = ApprovalWorkflowSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['model_name', 'is_active']
#     search_fields = ['name', 'description', 'model_name']
#
#     @action(detail=True, methods=['get'])
#     def steps(self, request, pk=None):
#         """Get workflow steps"""
#         workflow = self.get_object()
#         steps = workflow.steps.all().order_by('step_order')
#         serializer = ApprovalStepSerializer(steps, many=True)
#         return Response(success_response(serializer.data))
#
#
# class ApprovalStepViewSet(viewsets.ModelViewSet):
#     """ViewSet for ApprovalStep model"""
#     queryset = ApprovalStep.objects.select_related('workflow', 'role').all()
#     serializer_class = ApprovalStepSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['workflow', 'role', 'is_required']
#     search_fields = ['step_name', 'workflow__name', 'role__name']
#
#
# class ApprovalRequestViewSet(viewsets.ModelViewSet):
#     """ViewSet for ApprovalRequest model"""
#     queryset = ApprovalRequest.objects.select_related(
#         'workflow', 'requester', 'current_step'
#     ).prefetch_related('actions').all()
#     serializer_class = ApprovalRequestSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_fields = ['workflow', 'requester', 'status', 'current_step']
#     search_fields = ['workflow__name', 'requester__username']
#     ordering_fields = ['request_date', 'completion_date']
#     ordering = ['-request_date']
#
#     @action(detail=False, methods=['get'])
#     def pending(self, request):
#         """Get pending approval requests"""
#         requests = self.queryset.filter(status='PENDING')
#         serializer = self.get_serializer(requests, many=True)
#         return Response(success_response(serializer.data))
#
#     @action(detail=False, methods=['get'])
#     def my_pending(self, request):
#         """Get requests pending current user's approval"""
#         user_roles = request.user.user_roles.filter(is_active=True).values_list('role_id', flat=True)
#
#         requests = self.queryset.filter(
#             status='PENDING',
#             current_step__role_id__in=user_roles
#         )
#         serializer = self.get_serializer(requests, many=True)
#         return Response(success_response(serializer.data))
#
#     @action(detail=True, methods=['post'])
#     def approve(self, request, pk=None):
#         """Approve a request"""
#         approval_request = self.get_object()
#         comments = request.data.get('comments', '')
#
#         # Create approval action
#         ApprovalAction.objects.create(
#             request=approval_request,
#             step=approval_request.current_step,
#             user=request.user,
#             action='APPROVED',
#             comments=comments
#         )
#
#         # Move to next step or complete
#         next_step = ApprovalStep.objects.filter(
#             workflow=approval_request.workflow,
#             step_order__gt=approval_request.current_step.step_order
#         ).order_by('step_order').first()
#
#         if next_step:
#             approval_request.current_step = next_step
#         else:
#             approval_request.status = 'APPROVED'
#             approval_request.completion_date = timezone.now()
#             approval_request.current_step = None
#
#         approval_request.save()
#
#         serializer = self.get_serializer(approval_request)
#         return Response(success_response(serializer.data))
#
#     @action(detail=True, methods=['post'])
#     def reject(self, request, pk=None):
#         """Reject a request"""
#         approval_request = self.get_object()
#         comments = request.data.get('comments', '')
#
#         # Create rejection action
#         ApprovalAction.objects.create(
#             request=approval_request,
#             step=approval_request.current_step,
#             user=request.user,
#             action='REJECTED',
#             comments=comments
#         )
#
#         # Mark as rejected
#         approval_request.status = 'REJECTED'
#         approval_request.completion_date = timezone.now()
#         approval_request.save()
#
#         serializer = self.get_serializer(approval_request)
#         return Response(success_response(serializer.data))
#
#
# class ApprovalActionViewSet(viewsets.ReadOnlyModelViewSet):
#     """ViewSet for ApprovalAction model (read-only)"""
#     queryset = ApprovalAction.objects.select_related('request', 'step', 'user').all()
#     serializer_class = ApprovalActionSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_fields = ['request', 'step', 'user', 'action']
#     search_fields = ['user__username', 'comments']
#     ordering_fields = ['action_date']
#     ordering = ['-action_date']