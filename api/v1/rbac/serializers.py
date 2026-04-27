# """
# RBAC Serializers for Fleet Manager API
# Comprehensive serializers matching admin panel functionality
# """
#
# from rest_framework import serializers
# from rbac.models import (
#     Role, Permission, RolePermission, UserRole,
#     ApprovalWorkflow, ApprovalStep, ApprovalRequest, ApprovalAction
# )
# from security.models import CustomUser
#
#
# class PermissionSerializer(serializers.ModelSerializer):
#     """Serializer for Permission model"""
#     class Meta:
#         model = Permission
#         fields = [
#             'id', 'name', 'codename', 'description', 'module',
#             'is_active', 'created_at', 'updated_at'
#         ]
#
#
# class RoleSerializer(serializers.ModelSerializer):
#     """Comprehensive serializer for Role model"""
#     permission_count = serializers.SerializerMethodField()
#     user_count = serializers.SerializerMethodField()
#     permissions_detail = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Role
#         fields = [
#             'id', 'name', 'description', 'is_active', 'is_system_role',
#             'permission_count', 'user_count', 'permissions_detail',
#             'created_at', 'updated_at'
#         ]
#
#     def get_permission_count(self, obj):
#         """Get count of permissions for this role"""
#         return obj.role_permissions.filter(is_active=True).count()
#
#     def get_user_count(self, obj):
#         """Get count of users with this role"""
#         return obj.user_roles.filter(is_active=True).count()
#
#     def get_permissions_detail(self, obj):
#         """Get detailed permissions for this role"""
#         role_permissions = obj.role_permissions.filter(is_active=True).select_related('permission')
#         permissions = []
#
#         for rp in role_permissions:
#             permissions.append({
#                 'id': rp.permission.id,
#                 'name': rp.permission.name,
#                 'codename': rp.permission.codename,
#                 'module': rp.permission.module,
#                 'can_create': rp.can_create,
#                 'can_read': rp.can_read,
#                 'can_update': rp.can_update,
#                 'can_delete': rp.can_delete,
#                 'can_approve': rp.can_approve,
#             })
#
#         return permissions
#
#
# class RolePermissionSerializer(serializers.ModelSerializer):
#     """Serializer for RolePermission model"""
#     role_name = serializers.CharField(source='role.name', read_only=True)
#     permission_name = serializers.CharField(source='permission.name', read_only=True)
#     permission_codename = serializers.CharField(source='permission.codename', read_only=True)
#
#     class Meta:
#         model = RolePermission
#         fields = [
#             'id', 'role', 'role_name', 'permission', 'permission_name',
#             'permission_codename', 'can_create', 'can_read', 'can_update',
#             'can_delete', 'can_approve', 'is_active', 'created_at', 'updated_at'
#         ]
#
#
# class UserRoleSerializer(serializers.ModelSerializer):
#     """Serializer for UserRole model"""
#     user_name = serializers.CharField(source='user.get_full_name', read_only=True)
#     user_email = serializers.CharField(source='user.email', read_only=True)
#     role_name = serializers.CharField(source='role.name', read_only=True)
#
#     class Meta:
#         model = UserRole
#         fields = [
#             'id', 'user', 'user_name', 'user_email', 'role', 'role_name',
#             'assigned_date', 'is_active', 'created_at', 'updated_at'
#         ]
#
#
# class ApprovalWorkflowSerializer(serializers.ModelSerializer):
#     """Serializer for ApprovalWorkflow model"""
#     step_count = serializers.SerializerMethodField()
#
#     class Meta:
#         model = ApprovalWorkflow
#         fields = [
#             'id', 'name', 'description', 'model_name', 'is_active',
#             'step_count', 'created_at', 'updated_at'
#         ]
#
#     def get_step_count(self, obj):
#         """Get count of steps in workflow"""
#         return obj.steps.count()
#
#
# class ApprovalStepSerializer(serializers.ModelSerializer):
#     """Serializer for ApprovalStep model"""
#     workflow_name = serializers.CharField(source='workflow.name', read_only=True)
#     role_name = serializers.CharField(source='role.name', read_only=True)
#
#     class Meta:
#         model = ApprovalStep
#         fields = [
#             'id', 'workflow', 'workflow_name', 'step_order', 'step_name',
#             'role', 'role_name', 'is_required', 'can_skip',
#             'created_at', 'updated_at'
#         ]
#
#
# class ApprovalActionSerializer(serializers.ModelSerializer):
#     """Serializer for ApprovalAction model"""
#     user_name = serializers.CharField(source='user.get_full_name', read_only=True)
#     step_name = serializers.CharField(source='step.step_name', read_only=True)
#
#     class Meta:
#         model = ApprovalAction
#         fields = [
#             'id', 'request', 'step', 'step_name', 'user', 'user_name',
#             'action', 'comments', 'action_date', 'created_at', 'updated_at'
#         ]
#
#
# class ApprovalRequestSerializer(serializers.ModelSerializer):
#     """Comprehensive serializer for ApprovalRequest model"""
#     workflow_name = serializers.CharField(source='workflow.name', read_only=True)
#     requester_name = serializers.CharField(source='requester.get_full_name', read_only=True)
#     current_step_name = serializers.CharField(source='current_step.step_name', read_only=True)
#     actions = ApprovalActionSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = ApprovalRequest
#         fields = [
#             'id', 'workflow', 'workflow_name', 'object_id', 'content_type',
#             'requester', 'requester_name', 'request_date', 'status',
#             'current_step', 'current_step_name', 'completion_date',
#             'comments', 'actions', 'created_at', 'updated_at'
#         ]
#
#
# class UserSerializer(serializers.ModelSerializer):
#     """Serializer for CustomUser model"""
#     full_name = serializers.CharField(source='get_full_name', read_only=True)
#     roles = serializers.SerializerMethodField()
#
#     class Meta:
#         model = CustomUser
#         fields = [
#             'id', 'username', 'email', 'first_name', 'last_name',
#             'full_name', 'is_active', 'is_staff', 'is_superuser',
#             'last_login', 'date_joined', 'roles'
#         ]
#         read_only_fields = ['last_login', 'date_joined']
#
#     def get_roles(self, obj):
#         """Get user's roles"""
#         user_roles = obj.user_roles.filter(is_active=True).select_related('role')
#         return [
#             {
#                 'id': ur.role.id,
#                 'name': ur.role.name,
#                 'assigned_date': ur.assigned_date
#             }
#             for ur in user_roles
#         ]