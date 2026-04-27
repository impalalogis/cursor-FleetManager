from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.conf import settings

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
import json

class Permission(models.Model):
    """Permissions for different actions"""
    PERMISSION_CHOICES = [
        # Driver permissions
        ('VIEW_OWN_EXPENSES', 'View Own Expenses'),
        ('ADD_OWN_EXPENSES', 'Add Own Expenses'),
        ('VIEW_OWN_ADVANCES', 'View Own Advances'),
        ('REQUEST_ADVANCE', 'Request Advance'),
        ('VIEW_OWN_SHIPMENTS', 'View Own Shipments'),
        ('VIEW_OWN_BALANCE', 'View Own Balance'),

        # Transporter permissions
        ('VIEW_SHIPMENT_DETAILS', 'View Shipment Details'),
        ('VIEW_TRANSPORTER_SHIPMENTS', 'View Transporter Shipments'),

        # Company permissions
        ('VIEW_COMPANY_SHIPMENTS', 'View Company Shipments'),

        # Broker permissions
        ('VIEW_BROKER_SHIPMENTS', 'View Broker Shipments'),

        # Owner permissions
        ('VIEW_OWNER_VEHICLES', 'View Owner Vehicles'),
        ('VIEW_OWNER_SHIPMENTS', 'View Owner Shipments'),
        ('VIEW_OWNER_EXPENSES', 'View Owner Expenses'),

        # Operation permissions
        ('ADD_EXPENSE', 'Add Expense'),
        ('ADD_CONSIGNMENT', 'Add Consignment'),
        ('EDIT_OPERATION_DETAILS', 'Edit Operation Details'),
        ('APPROVE_DRIVER_EXPENSES', 'Approve Driver Expenses'),
        ('APPROVE_DRIVER_ADVANCES', 'Approve Driver Advances'),

        # Finance permissions
        ('VIEW_FINANCIAL_DETAILS', 'View Financial Details'),
        ('APPROVE_FINANCIAL_TRANSACTIONS', 'Approve Financial Transactions'),
        ('MANAGE_INVOICES', 'Manage Invoices'),
        ('MANAGE_PAYMENTS', 'Manage Payments'),

        # Superuser permissions
        ('ALL_ACCESS', 'All Access'),
        ('CREATE_ENTITIES', 'Create All Entities'),
        ('MANAGE_USERS', 'Manage Users'),
        ('MANAGE_ROLES', 'Manage Roles'),
    ]

    name = models.CharField(max_length=50, choices=PERMISSION_CHOICES, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_permission'

    def __str__(self):
        return self.get_name_display()

    def get_roles_list(self):
        """Get list of role names that have this permission"""
        return list(self.roles.values_list('name', flat=True))

    def get_roles_display(self):
        """Get formatted display of roles for admin"""
        roles = self.roles.all()
        if not roles:
            return "No roles assigned"
        return " | ".join([role.get_name_display() for role in roles])

    def assign_to_role(self, role):
        """Assign this permission to a role"""
        if isinstance(role, str):
            role = Role.objects.get(name=role)
        RolePermission.objects.get_or_create(role=role, permission=self)

    def remove_from_role(self, role):
        """Remove this permission from a role"""
        if isinstance(role, str):
            role = Role.objects.get(name=role)
        RolePermission.objects.filter(role=role, permission=self).delete()


class Role(models.Model):
    """Role-based access control roles"""
    ROLE_CHOICES = [
        ('DRIVER', 'Driver'),
        ('TRANSPORTER', 'Transporter'),
        ('CONSIGNOR-AND-CONSIGNEE', 'Company'),
        ('BROKER', 'Broker'),
        ('OWNER', 'Owner'),
        ('OPERATION', 'Operation'),
        ('FINANCE', 'Finance'),
        ('SUPERUSER', 'Superuser'),
    ]

    name = models.CharField(max_length=40, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)

    # Direct many-to-many relationship for easier management
    permissions = models.ManyToManyField(
        'Permission',
        through='RolePermission',
        related_name='roles',
        blank=True,
        help_text="Permissions assigned to this role"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_role'

    def __str__(self):
        return self.get_name_display()

    def get_permissions_list(self):
        """Get list of permission names for this role"""
        return list(self.permissions.values_list('name', flat=True))

    def get_permissions_display(self):
        """Get formatted display of permissions for admin"""
        permissions = self.permissions.all()
        if not permissions:
            return "No permissions assigned"
        return " | ".join([perm.get_name_display() for perm in permissions])

    def add_permission(self, permission):
        """Add a permission to this role"""
        if isinstance(permission, str):
            permission = Permission.objects.get(name=permission)
        RolePermission.objects.get_or_create(role=self, permission=permission)

    def remove_permission(self, permission):
        """Remove a permission from this role"""
        if isinstance(permission, str):
            permission = Permission.objects.get(name=permission)
        RolePermission.objects.filter(role=self, permission=permission).delete()

    def has_permission(self, permission_name):
        """Check if this role has a specific permission"""
        return self.permissions.filter(name=permission_name).exists()


class RolePermission(models.Model):
    """Many-to-many relationship between roles and permissions"""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_role_permission'
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role} - {self.permission}"


class UserRole(models.Model):
    """User to role assignment"""
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    entity = models.ForeignKey('entity.Organization', on_delete=models.CASCADE, null=True, blank=True,
                               help_text="Organization this role applies to")
    driver = models.ForeignKey('entity.Driver', on_delete=models.CASCADE, null=True, blank=True,
                               help_text="Driver this role applies to")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_user_role'
        unique_together = ('user', 'role', 'entity', 'driver')

    def __str__(self):
        entity_str = f" ({self.entity})" if self.entity else ""
        driver_str = f" ({self.driver})" if self.driver else ""
        return f"{self.user.username} - {self.role}{entity_str}{driver_str}"


class ApprovalWorkflow(models.Model):
    """Approval workflow configuration"""
    WORKFLOW_TYPES = [
        ('EXPENSE_APPROVAL', 'Expense Approval'),
        ('ADVANCE_APPROVAL', 'Advance Approval'),
        ('INVOICE_APPROVAL', 'Invoice Approval'),
    ]

    name = models.CharField(max_length=100)
    workflow_type = models.CharField(max_length=20, choices=WORKFLOW_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_approval_workflow'

    def __str__(self):
        return f"{self.name} ({self.get_workflow_type_display()})"


class ApprovalStep(models.Model):
    """Individual steps in approval workflow"""
    workflow = models.ForeignKey(ApprovalWorkflow, on_delete=models.CASCADE, related_name='steps')
    step_order = models.PositiveIntegerField()
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='approval_steps')
    is_required = models.BooleanField(default=True)
    can_override = models.BooleanField(default=False,
                                       help_text="Can this step be overridden by higher authority?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_approval_step'
        unique_together = ('workflow', 'step_order')
        ordering = ['workflow', 'step_order']

    def __str__(self):
        return f"{self.workflow.name} - Step {self.step_order} ({self.role})"


class ApprovalRequest(models.Model):
    """Individual approval requests"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Content type fields for different types of requests
    content_type = models.CharField(max_length=50)  # 'expense', 'advance', 'invoice'
    object_id = models.PositiveIntegerField()

    # Request details
    requester = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='approval_requests')
    workflow = models.ForeignKey(ApprovalWorkflow, on_delete=models.CASCADE, related_name='approval_requests')
    current_step = models.ForeignKey(ApprovalStep, on_delete=models.CASCADE, related_name='current_approval_requests')

    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    request_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(null=True, blank=True)

    # Request details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'users_approval_request'
        unique_together = ('content_type', 'object_id')

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


class ApprovalAction(models.Model):
    """Individual approval actions taken by users"""
    ACTION_CHOICES = [
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('CANCEL', 'Cancel'),
        ('OVERRIDE', 'Override'),
    ]

    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name='actions')
    approver = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='approval_actions')
    step = models.ForeignKey(ApprovalStep, on_delete=models.CASCADE, related_name='approval_actions')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    comments = models.TextField(blank=True)
    action_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_approval_action'
        unique_together = ('approval_request', 'step')

    def __str__(self):
        return f"{self.approval_request.title} - {self.get_action_display()} by {self.approver.username}"


# Utility functions for RBAC
class RBACManager:
    @staticmethod
    def get_user_permissions(user):
        """Get all permissions for a user"""
        user_roles = UserRole.objects.filter(user=user, is_active=True)
        permissions = set()

        for user_role in user_roles:
            role_permissions = RolePermission.objects.filter(role=user_role.role)
            for rp in role_permissions:
                permissions.add(rp.permission.name)

        return list(permissions)

    @staticmethod
    def has_permission(user, permission_name):
        """Check if user has specific permission"""
        return permission_name in RBACManager.get_user_permissions(user)

    @staticmethod
    def get_user_roles(user):
        """Get all roles for a user"""
        return UserRole.objects.filter(user=user, is_active=True)

    @staticmethod
    def can_access_entity(user, entity_type, entity_id):
        """Check if user can access specific entity"""
        user_roles = RBACManager.get_user_roles(user)

        for user_role in user_roles:
            # Superuser can access everything
            if user_role.role.name == 'SUPERUSER':
                return True

            # Check entity-specific access
            if entity_type == 'driver' and user_role.driver_id == entity_id:
                return True
            elif entity_type == 'organization' and user_role.entity_id == entity_id:
                return True

        return False

    @staticmethod
    def create_approval_request(content_type, object_id, requester, title, description, amount=None):
        """Create a new approval request"""
        # Determine workflow type based on content type
        workflow_type_map = {
            'expense': 'EXPENSE_APPROVAL',
            'advance': 'ADVANCE_APPROVAL',
            'invoice': 'INVOICE_APPROVAL',
        }

        workflow_type = workflow_type_map.get(content_type)
        if not workflow_type:
            raise ValueError(f"Unknown content type: {content_type}")

        # Get active workflow
        workflow = ApprovalWorkflow.objects.filter(
            workflow_type=workflow_type,
            is_active=True
        ).first()

        if not workflow:
            raise ValueError(f"No active workflow found for {workflow_type}")

        # Get first step
        first_step = workflow.steps.filter(step_order=1).first()
        if not first_step:
            raise ValueError(f"No steps found for workflow {workflow.name}")

        # Create approval request
        approval_request = ApprovalRequest.objects.create(
            content_type=content_type,
            object_id=object_id,
            requester=requester,
            workflow=workflow,
            current_step=first_step,
            title=title,
            description=description,
            amount=amount
        )

        return approval_request

    @staticmethod
    def process_approval(approval_request, approver, action, comments=""):
        """Process an approval action"""
        # Check if approver has permission for current step
        user_roles = RBACManager.get_user_roles(approver)
        current_step_role = approval_request.current_step.role

        has_permission = False
        for user_role in user_roles:
            if user_role.role == current_step_role:
                has_permission = True
                break

        if not has_permission:
            raise PermissionError(f"User {approver.username} does not have permission for step {current_step_role}")

        # Create approval action
        approval_action = ApprovalAction.objects.create(
            approval_request=approval_request,
            approver=approver,
            step=approval_request.current_step,
            action=action,
            comments=comments
        )

        # Update approval request status
        if action in ['REJECT', 'CANCEL']:
            approval_request.status = action
            approval_request.completed_date = approval_action.action_date
            approval_request.save()
        elif action == 'APPROVE':
            # Move to next step or complete
            next_step = approval_request.workflow.steps.filter(
                step_order__gt=approval_request.current_step.step_order
            ).order_by('step_order').first()

            if next_step:
                approval_request.current_step = next_step
                approval_request.save()
            else:
                # No more steps, approval complete
                approval_request.status = 'APPROVED'
                approval_request.completed_date = approval_action.action_date
                approval_request.save()

        return approval_action




class CustomUser(AbstractUser):
    """Extended user model with security features and multi-tenant support"""

    # Security fields
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    last_password_change = models.DateTimeField(auto_now_add=True)
    password_expires_at = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)

    # Profile fields
    phone_number = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    # Fix reverse accessor conflicts with unique related_names
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='security_user_set',
        related_query_name='security_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='security_user_set',
        related_query_name='security_user',
    )

    # Direct many-to-many relationship for roles (easier management)
    roles = models.ManyToManyField(
        'users.Role',
        through='users.UserRole',
        related_name='users',
        blank=True,
        help_text="Roles assigned to this user"
    )

    class Meta:
        db_table = 'auth_custom_user'

    def is_account_locked(self):
        """Check if account is currently locked"""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False

    def is_password_expired(self):
        """Check if password has expired"""
        if self.password_expires_at:
            return timezone.now() > self.password_expires_at
        return False

    def lock_account(self, duration_minutes=30):
        """Lock account for specified duration"""
        self.account_locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save()

    def unlock_account(self):
        """Unlock account and reset failed login attempts"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save()

    def can_login(self):
        """Check if user can login (not locked and active)"""
        return self.is_active and not self.is_account_locked()

    def get_user_roles(self):
        """Get all active roles for this user"""
        from models import UserRole
        return UserRole.objects.filter(user=self, is_active=True)

    def get_roles_list(self):
        """Get list of role names for this user"""
        return list(self.roles.values_list('name', flat=True))

    def get_roles_display(self):
        """Get formatted display of roles for admin"""
        user_roles = self.get_user_roles()
        if not user_roles:
            return "No roles assigned"

        role_strings = []
        for user_role in user_roles:
            role_str = user_role.role.get_name_display()
            if user_role.entity:
                role_str += f" ({user_role.entity})"
            elif user_role.driver:
                role_str += f" ({user_role.driver})"
            role_strings.append(role_str)

        return " | ".join(role_strings)

    # def get_tenant_display(self):
    #     """Get tenant display name for admin"""
    #     if self.tenant:
    #         return f"{self.tenant.organization_name} ({self.tenant.organization_type})"
    #     return "No tenant assigned"

    # def can_access_tenant(self, tenant):
    #     """Check if user can access a specific tenant"""
    #     # Superusers can access any tenant
    #     if self.is_superuser:
    #         return True
    #
    #     # Check primary tenant
    #     if self.tenant == tenant:
    #         return True
    #
    #     # Check additional tenant permissions
    #     return self.tenant_permissions.filter(tenant=tenant, is_active=True).exists()
    #
    # def get_accessible_tenants(self):
    #     """Get all tenants this user can access"""
    #     from entity.models import Organization
    #
    #     if self.is_superuser:
    #         return Organization.objects.filter(is_active=True)
    #
    #     accessible_tenants = []
    #
    #     # Add primary tenant
    #     if self.tenant and self.tenant.is_active:
    #         accessible_tenants.append(self.tenant.id)

    # Add tenants from permissions
    # permission_tenant_ids = self.tenant_permissions.filter(
    #     is_active=True
    # ).values_list('tenant_id', flat=True)
    # accessible_tenants.extend(permission_tenant_ids)
    #
    # return Organization.objects.filter(
    #     id__in=accessible_tenants,
    #     is_active=True
    # ).distinct()

    # def switch_to_tenant(self, tenant):
    #     """Switch user's active tenant context (for session)"""
    #     if self.can_access_tenant(tenant):
    #         # This would be handled by middleware/session
    #         return True
    #     return False
    #
    def add_role(self, role, entity=None, driver=None):
        """Add a role to this user"""
        # from .models import UserRole, Role

        if isinstance(role, str):
            role = Role.objects.get(name=role)

        user_role, created = UserRole.objects.get_or_create(
            user=self,
            role=role,
            entity=entity,
            driver=driver,
            defaults={'is_active': True}
        )

        if not created and not user_role.is_active:
            user_role.is_active = True
            user_role.save()

        return user_role

    def remove_role(self, role, entity=None, driver=None):
        """Remove a role from this user"""
        # from users.models import UserRole, Role

        if isinstance(role, str):
            role = Role.objects.get(name=role)

        UserRole.objects.filter(
            user=self,
            role=role,
            entity=entity,
            driver=driver
        ).update(is_active=False)

    def has_role(self, role_name):
        """Check if user has a specific role"""
        return self.get_user_roles().filter(role__name=role_name).exists()

    def get_all_permissions(self):
        """Get all permissions from all user's roles"""
        # from users.models import usersManager
        return RBACManager.get_user_permissions(self)

    def has_permission(self, permission_name):
        """Check if user has a specific permission through roles"""
        # from rbac.models import RBACManager
        return RBACManager.has_permission(self, permission_name)


class SecurityEvent(models.Model):
    """Log security-related events"""

    EVENT_TYPES = [
        ('LOGIN_SUCCESS', 'Successful Login'),
        ('LOGIN_FAILED', 'Failed Login'),
        ('LOGOUT', 'Logout'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('ACCOUNT_LOCKED', 'Account Locked'),
        ('ACCOUNT_UNLOCKED', 'Account Unlocked'),
        ('PERMISSION_DENIED', 'Permission Denied'),
        ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity'),
        ('DATA_ACCESS', 'Data Access'),
        ('DATA_MODIFICATION', 'Data Modification'),
        ('SECURITY_VIOLATION', 'Security Violation'),
        ('RATE_LIMIT_EXCEEDED', 'Rate Limit Exceeded'),
        ('INVALID_TOKEN', 'Invalid Token'),
        ('SESSION_TIMEOUT', 'Session Timeout'),
        ('TWO_FACTOR_AUTH', 'Two-Factor Authentication'),
    ]

    SEVERITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events'
    )
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='LOW')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    description = models.TextField()
    additional_data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Request context
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_params = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'security_event'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['severity', 'timestamp']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{self.event_type} - {user_str} - {self.timestamp}"

    @classmethod
    def log_event(cls, event_type, user=None, ip_address=None, description='',
                  severity='LOW', request=None, **additional_data):
        """Convenience method to log security events"""
        event_data = {
            'event_type': event_type,
            'user': user,
            'ip_address': ip_address or '127.0.0.1',
            'description': description,
            'severity': severity,
            'additional_data': additional_data,
        }

        if request:
            event_data.update({
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'request_method': request.method,
                'request_path': request.path,
                'request_params': dict(request.GET.items()) if request.GET else {},
            })

        return cls.objects.create(**event_data)


class AuditLog(models.Model):
    """Comprehensive audit logging for data changes"""

    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=10, choices=ACTION_TYPES)
    content_type = models.CharField(max_length=100)  # Model name
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=200)

    # Change tracking
    changes = models.JSONField(default=dict, blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)

    # Context
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)

    # Additional metadata
    reason = models.TextField(blank=True)
    additional_info = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"{user_str} {self.action} {self.content_type} {self.object_id}"


class RateLimitTracker(models.Model):
    """Track rate limiting for users and IPs"""

    identifier = models.CharField(max_length=100)  # IP or user ID
    identifier_type = models.CharField(max_length=10, choices=[('IP', 'IP'), ('USER', 'User')])
    endpoint = models.CharField(max_length=200)
    request_count = models.PositiveIntegerField(default=1)
    window_start = models.DateTimeField(auto_now_add=True)
    last_request = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rate_limit_tracker'
        unique_together = ['identifier', 'identifier_type', 'endpoint']
        indexes = [
            models.Index(fields=['identifier', 'window_start']),
            models.Index(fields=['endpoint', 'window_start']),
        ]


class LoginAttempt(models.Model):
    """Track login attempts for security monitoring"""

    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    success = models.BooleanField()
    failure_reason = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'login_attempt'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['username', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['success', 'timestamp']),
        ]


class SecurityConfiguration(models.Model):
    """Store security configuration settings"""

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        db_table = 'security_configuration'

    def get_value(self):
        """Get parsed value (handles JSON, boolean, int)"""
        try:
            return json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            return self.value

    @classmethod
    def get_setting(cls, key, default=None):
        """Get security setting value"""
        try:
            config = cls.objects.get(key=key, is_active=True)
            return config.get_value()
        except cls.DoesNotExist:
            return default


class TenantPermission(models.Model):
    """
    Model to manage additional tenant access permissions for users.
    This allows users to access multiple tenants beyond their primary tenant.
    """
    PERMISSION_TYPES = [
        ('READ', 'Read Only'),
        ('WRITE', 'Read/Write'),
        ('ADMIN', 'Admin'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='tenant_permissions'
    )
    tenant = models.ForeignKey(
        'entity.Organization',
        on_delete=models.CASCADE,
        related_name='user_permissions'
    )
    permission_type = models.CharField(
        max_length=10,
        choices=PERMISSION_TYPES,
        default='READ'
    )
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions',
        help_text="User who granted this permission"
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date for this permission"
    )
    notes = models.TextField(blank=True, help_text="Additional notes about this permission")

    class Meta:
        db_table = 'security_tenant_permission'
        unique_together = ('user', 'tenant')
        indexes = [
            models.Index(fields=['user', 'tenant']),
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.tenant.organization_name} ({self.permission_type})"

    def is_expired(self):
        """Check if this permission has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def is_valid(self):
        """Check if this permission is currently valid"""
        return self.is_active and not self.is_expired()

    def can_read(self):
        """Check if this permission allows read access"""
        return self.is_valid() and self.permission_type in ['READ', 'WRITE', 'ADMIN']

    def can_write(self):
        """Check if this permission allows write access"""
        return self.is_valid() and self.permission_type in ['WRITE', 'ADMIN']

    def can_admin(self):
        """Check if this permission allows admin access"""
        return self.is_valid() and self.permission_type == 'ADMIN'