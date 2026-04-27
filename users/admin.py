# from django.contrib import admin
# from django.utils.html import format_html
# from django.db import models
# from django.forms import CheckboxSelectMultiple
# from .models import (
#     Role, Permission, RolePermission, UserRole,
#     ApprovalWorkflow, ApprovalStep, ApprovalRequest, ApprovalAction
# )
#
#
# class RolePermissionInline(admin.TabularInline):
#     model = RolePermission
#     extra = 0
#     autocomplete_fields = ['permission']
#     verbose_name = "Permission"
#     verbose_name_plural = "Permissions"
#
#
# @admin.register(Role)
# class RoleAdmin(admin.ModelAdmin):
#     list_display = [
#         'name', 'description', 'get_permissions_count',
#         'get_users_count', 'created_at', 'updated_at'
#     ]
#     list_filter = ['name', 'created_at']
#     search_fields = ['name', 'description']
#     readonly_fields = [
#         'created_at', 'updated_at', 'get_permissions_display',
#         'get_users_count', 'get_permissions_count'
#     ]
#
#     fieldsets = (
#         ('Role Information', {
#             'fields': ('name', 'description')
#         }),
#         ('Role Summary', {
#             'fields': ('get_permissions_display', 'get_permissions_count', 'get_users_count'),
#             'classes': ('collapse',),
#             'description': 'Summary of permissions and users assigned to this role.'
#         }),
#         ('Audit Information', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
#
#     inlines = [RolePermissionInline]
#
#     def get_permissions_count(self, obj):
#         """Display count of permissions assigned to this role"""
#         return obj.permissions.count()
#
#     get_permissions_count.short_description = "Permissions Count"
#
#     def get_users_count(self, obj):
#         """Display count of users with this role"""
#         return obj.user_roles.filter(is_active=True).count()
#
#     get_users_count.short_description = "Users Count"
#
#     def get_permissions_display(self, obj):
#         """Display all permissions for this role"""
#         return obj.get_permissions_display()
#
#     get_permissions_display.short_description = "Assigned Permissions"
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).prefetch_related(
#             'permissions', 'user_roles'
#         )
#
#     actions = ['assign_all_permissions', 'clear_all_permissions']
#
#     def assign_all_permissions(self, request, queryset):
#         """Assign all available permissions to selected roles"""
#         all_permissions = Permission.objects.all()
#         for role in queryset:
#             for permission in all_permissions:
#                 role.add_permission(permission)
#         self.message_user(request, f"Assigned all permissions to {queryset.count()} roles.")
#
#     assign_all_permissions.short_description = "Assign all permissions to selected roles"
#
#     def clear_all_permissions(self, request, queryset):
#         """Clear all permissions from selected roles"""
#         for role in queryset:
#             role.permissions.clear()
#         self.message_user(request, f"Cleared all permissions from {queryset.count()} roles.")
#
#     clear_all_permissions.short_description = "Clear all permissions from selected roles"
#
#
# @admin.register(Permission)
# class PermissionAdmin(admin.ModelAdmin):
#     list_display = [
#         'name', 'description', 'get_roles_count', 'created_at'
#     ]
#     list_filter = ['name', 'created_at']
#     search_fields = ['name', 'description']
#     readonly_fields = [
#         'created_at', 'get_roles_display', 'get_roles_count'
#     ]
#
#     fieldsets = (
#         ('Permission Information', {
#             'fields': ('name', 'description')
#         }),
#         ('Role Assignment Summary', {
#             'fields': ('get_roles_display', 'get_roles_count'),
#             'classes': ('collapse',),
#             'description': 'Shows which roles have this permission.'
#         }),
#         ('Audit Information', {
#             'fields': ('created_at',),
#             'classes': ('collapse',)
#         })
#     )
#
#     def get_roles_count(self, obj):
#         """Display count of roles that have this permission"""
#         return obj.roles.count()
#
#     get_roles_count.short_description = "Roles Count"
#
#     def get_roles_display(self, obj):
#         """Display all roles that have this permission"""
#         return obj.get_roles_display()
#
#     get_roles_display.short_description = "Assigned to Roles"
#
#
# @admin.register(RolePermission)
# class RolePermissionAdmin(admin.ModelAdmin):
#     list_display = ['role', 'permission', 'created_at']
#     list_filter = ['role', 'permission', 'created_at']
#     search_fields = ['role__name', 'permission__name']
#     autocomplete_fields = ['role', 'permission']
#     readonly_fields = ['created_at']
#
#     # Group by role for better organization
#     list_select_related = ['role', 'permission']
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('role', 'permission')
#
#
# class UserRoleInline(admin.TabularInline):
#     model = UserRole
#     extra = 0
#     autocomplete_fields = ['role', 'entity', 'driver']
#     readonly_fields = ['created_at']
#     verbose_name = "User Role"
#     verbose_name_plural = "User Roles"
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'role', 'entity', 'driver'
#         )
#
#
# @admin.register(UserRole)
# class UserRoleAdmin(admin.ModelAdmin):
#     list_display = [
#         'user', 'role', 'entity', 'driver', 'is_active',
#         'created_at', 'updated_at'
#     ]
#     list_filter = [
#         'role', 'is_active', 'created_at', 'entity__organization_type'
#     ]
#     search_fields = [
#         'user__username', 'user__email', 'user__first_name',
#         'user__last_name', 'role__name'
#     ]
#     autocomplete_fields = ['user', 'role', 'entity', 'driver']
#     readonly_fields = ['created_at', 'updated_at']
#
#     fieldsets = (
#         ('User Role Assignment', {
#             'fields': ('user', 'role', 'is_active')
#         }),
#         ('Context (Optional)', {
#             'fields': ('entity', 'driver'),
#             'description': 'Specify the context for this role assignment (organization or driver specific).'
#         }),
#         ('Audit Information', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'user', 'role', 'entity', 'driver'
#         ).prefetch_related('role__permissions')
#
#     actions = ['activate_roles', 'deactivate_roles']
#
#     def activate_roles(self, request, queryset):
#         """Activate selected user roles"""
#         updated = queryset.update(is_active=True)
#         self.message_user(request, f"Activated {updated} user roles.")
#
#     activate_roles.short_description = "Activate selected user roles"
#
#     def deactivate_roles(self, request, queryset):
#         """Deactivate selected user roles"""
#         updated = queryset.update(is_active=False)
#         self.message_user(request, f"Deactivated {updated} user roles.")
#
#     deactivate_roles.short_description = "Deactivate selected user roles"
#
#
# class ApprovalStepInline(admin.TabularInline):
#     model = ApprovalStep
#     extra = 1
#     autocomplete_fields = ['role']
#     ordering = ['step_order']
#
#
# @admin.register(ApprovalWorkflow)
# class ApprovalWorkflowAdmin(admin.ModelAdmin):
#     list_display = ['name', 'workflow_type', 'is_active', 'created_at']
#     list_filter = ['workflow_type', 'is_active', 'created_at']
#     search_fields = ['name', 'description']
#     readonly_fields = ['created_at']
#     inlines = [ApprovalStepInline]
#
#
# @admin.register(ApprovalStep)
# class ApprovalStepAdmin(admin.ModelAdmin):
#     list_display = ['workflow', 'step_order', 'role', 'is_required', 'can_override']
#     list_filter = ['workflow', 'role', 'is_required', 'can_override']
#     search_fields = ['workflow__name', 'role__name']
#     autocomplete_fields = ['workflow', 'role']
#     ordering = ['workflow', 'step_order']
#     readonly_fields = ['created_at']
#
#
# class ApprovalActionInline(admin.TabularInline):
#     model = ApprovalAction
#     extra = 0
#     readonly_fields = ['approver', 'step', 'action', 'comments', 'action_date']
#     can_delete = False
#
#     def has_add_permission(self, request, obj=None):
#         return False
#
#
# @admin.register(ApprovalRequest)
# class ApprovalRequestAdmin(admin.ModelAdmin):
#     list_display = [
#         'title', 'content_type', 'object_id', 'requester',
#         'status', 'current_step', 'amount', 'request_date'
#     ]
#     list_filter = ['content_type', 'status', 'workflow', 'request_date']
#     search_fields = ['title', 'description', 'requester__username']
#     readonly_fields = [
#         'content_type', 'object_id', 'requester', 'workflow',
#         'request_date', 'completed_date'
#     ]
#     autocomplete_fields = ['requester', 'workflow', 'current_step']
#     inlines = [ApprovalActionInline]
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'requester', 'workflow', 'current_step'
#         ).prefetch_related('actions')
#
#     def has_add_permission(self, request):
#         return False  # Approval requests should be created programmatically
#
#
# @admin.register(ApprovalAction)
# class ApprovalActionAdmin(admin.ModelAdmin):
#     list_display = [
#         'approval_request', 'approver', 'step', 'action',
#         'action_date', 'comments_preview'
#     ]
#     list_filter = ['action', 'step__role', 'action_date']
#     search_fields = [
#         'approval_request__title', 'approver__username',
#         'comments'
#     ]
#     readonly_fields = ['approval_request', 'approver', 'step', 'action_date']
#     autocomplete_fields = ['approval_request', 'approver', 'step']
#
#     def comments_preview(self, obj):
#         if obj.comments:
#             return obj.comments[:50] + "..." if len(obj.comments) > 50 else obj.comments
#         return "-"
#
#     comments_preview.short_description = "Comments"
#
#     def has_add_permission(self, request):
#         return False  # Approval actions should be created programmatically


# from .models import CustomUser, SecurityEvent, UserRole
# from rbac.models import UserRole

#
# class UserRoleInline(admin.TabularInline):
#     model = UserRole
#     extra = 0
#     autocomplete_fields = ['role', 'entity', 'driver']
#     readonly_fields = ['created_at', 'updated_at']
#     verbose_name = "Role Assignment"
#     verbose_name_plural = "Role Assignments"
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'role', 'entity', 'driver'
#         )
#
#
# @admin.register(CustomUser)
# class CustomUserAdmin(UserAdmin):
#     # Add role-related fields to the user admin
#     list_display = [
#         'username', 'email', 'first_name', 'last_name',
#         'get_roles_display', 'is_active', 'is_staff',
#         'last_login', 'date_joined'
#     ]
#
#     list_filter = [
#         'is_active', 'is_staff', 'is_superuser',
#         'user_roles__role', 'user_roles__is_active',
#         'date_joined', 'last_login'
#     ]
#
#     search_fields = [
#         'username', 'first_name', 'last_name', 'email',
#         'employee_id', 'phone_number'
#     ]
#
#     readonly_fields = [
#         'last_login', 'date_joined', 'created_at', 'updated_at',
#         'get_roles_display', 'get_all_permissions_display',
#         'failed_login_attempts'
#     ]
#
#     # Use filter_horizontal for easy role selection
#     filter_horizontal = ('groups', 'user_permissions')
#
#     # Enhanced fieldsets
#     fieldsets = (
#         (None, {
#             'fields': ('username', 'password')
#         }),
#         ('Personal info', {
#             'fields': (
#                 'first_name', 'last_name', 'email',
#                 'phone_number', 'employee_id', 'department'
#             )
#         }),
#         ('Role Management', {
#             'fields': (
#                 'get_roles_display', 'get_all_permissions_display'
#             ),
#             'description': 'User roles are managed through the Role Assignments section below. Roles determine what permissions the user has.'
#         }),
#         ('Permissions', {
#             'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
#             'classes': ('collapse',)
#         }),
#         ('Security Information', {
#             'fields': (
#                 'failed_login_attempts', 'account_locked_until',
#                 # 'last_password_change', 'password_expires_at',
#                 'two_factor_enabled', 'last_login_ip'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('Important dates', {
#             'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
#
#     # Add fieldsets for user creation
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('username', 'password1', 'password2'),
#         }),
#         ('Personal info', {
#             'fields': (
#                 'first_name', 'last_name', 'email',
#                 'phone_number', 'employee_id', 'department'
#             )
#         }),
#         ('Permissions', {
#             'fields': ('is_active', 'is_staff', 'is_superuser'),
#         }),
#     )
#
#     inlines = [UserRoleInline]
#
#     def get_roles_display(self, obj):
#         """Display user's roles in list view"""
#         return obj.get_roles_display()
#
#     get_roles_display.short_description = "Roles"
#
#     def get_all_permissions_display(self, obj):
#         """Display all permissions from user's roles"""
#         permissions = obj.get_all_permissions()
#         if not permissions:
#             return "No permissions"
#
#         # Group permissions by category for better display
#         permission_groups = {}
#         for perm in permissions:
#             # Extract category from permission name (e.g., 'VIEW_OWN_EXPENSES' -> 'VIEW')
#             category = perm.split('_')[0] if '_' in perm else 'OTHER'
#             if category not in permission_groups:
#                 permission_groups[category] = []
#             permission_groups[category].append(perm)
#
#         # Format for display
#         display_parts = []
#         for category, perms in permission_groups.items():
#             display_parts.append(f"{category}: {len(perms)} permissions")
#
#         return " | ".join(display_parts)
#
#     get_all_permissions_display.short_description = "All Permissions"
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).prefetch_related(
#             'user_roles__role', 'user_roles__entity', 'user_roles__driver',
#             'roles', 'groups', 'user_permissions'
#         )
#
#     actions = ['activate_users', 'deactivate_users', 'unlock_accounts', 'reset_failed_attempts']
#
#     def activate_users(self, request, queryset):
#         """Activate selected users"""
#         updated = queryset.update(is_active=True)
#         self.message_user(request, f"Activated {updated} users.")
#
#     activate_users.short_description = "Activate selected users"
#
#     def deactivate_users(self, request, queryset):
#         """Deactivate selected users"""
#         updated = queryset.update(is_active=False)
#         self.message_user(request, f"Deactivated {updated} users.")
#
#     deactivate_users.short_description = "Deactivate selected users"
#
#     def unlock_accounts(self, request, queryset):
#         """Unlock selected user accounts"""
#         updated = queryset.update(
#             account_locked_until=None,
#             failed_login_attempts=0
#         )
#         self.message_user(request, f"Unlocked {updated} user accounts.")
#
#     unlock_accounts.short_description = "Unlock selected accounts"
#
#     def reset_failed_attempts(self, request, queryset):
#         """Reset failed login attempts for selected users"""
#         updated = queryset.update(failed_login_attempts=0)
#         self.message_user(request, f"Reset failed attempts for {updated} users.")
#
#     reset_failed_attempts.short_description = "Reset failed login attempts"
#
#
# @admin.register(SecurityEvent)
# class SecurityEventAdmin(admin.ModelAdmin):
#     list_display = [
#         'event_type', 'user', 'ip_address', 'timestamp',
#         'details_preview'
#     ]
#     list_filter = ['event_type', 'timestamp']
#     search_fields = ['user__username', 'ip_address', 'details']
#     readonly_fields = ['timestamp']
#     date_hierarchy = 'timestamp'
#
#     def details_preview(self, obj):
#         if obj.details:
#             return obj.details[:50] + "..." if len(obj.details) > 50 else obj.details
#         return "-"
#
#     details_preview.short_description = "Details"
#
#     def has_add_permission(self, request):
#         return False  # Security events should be created programmatically
#
#     def has_change_permission(self, request, obj=None):
#         return False  # Security events should not be modified
