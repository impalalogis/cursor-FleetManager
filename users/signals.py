"""
Security signals for FleetManager application

Provides automated security event handling and monitoring
"""

import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import SecurityEvent, AuditLog
from .utils import get_client_ip

User = get_user_model()
logger = logging.getLogger('security')


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    """Log successful login events"""
    client_ip = get_client_ip(request)
    
    # Update user's last login IP
    if hasattr(user, 'last_login_ip'):
        user.last_login_ip = client_ip
        user.failed_login_attempts = 0  # Reset failed attempts on successful login
        user.save(update_fields=['last_login_ip', 'failed_login_attempts'])
    
    # Log security event
    SecurityEvent.log_event(
        'LOGIN_SUCCESS',
        user=user,
        ip_address=client_ip,
        description=f"User {user.username} logged in successfully",
        severity='LOW',
        request=request
    )
    
    logger.info(f"Successful login for user {user.username} from IP {client_ip}")


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    """Log user logout events"""
    if user and hasattr(user, 'username'):
        client_ip = get_client_ip(request)
        
        SecurityEvent.log_event(
            'LOGOUT',
            user=user,
            ip_address=client_ip,
            description=f"User {user.username} logged out",
            severity='LOW',
            request=request
        )
        
        logger.info(f"User {user.username} logged out from IP {client_ip}")


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Log failed login attempts and handle account lockout"""
    username = credentials.get('username', 'Unknown')
    client_ip = get_client_ip(request)
    
    # Try to find the user to update failed attempts
    try:
        user = User.objects.get(username=username)
        user.failed_login_attempts += 1
        
        # Check if account should be locked
        from django.conf import settings
        max_attempts = getattr(settings, 'SECURITY_SETTINGS', {}).get('MAX_LOGIN_ATTEMPTS', 5)
        
        if user.failed_login_attempts >= max_attempts:
            lockout_duration = getattr(settings, 'SECURITY_SETTINGS', {}).get('LOGIN_ATTEMPT_TIMEOUT', 300) // 60
            user.lock_account(duration_minutes=lockout_duration)
            
            SecurityEvent.log_event(
                'ACCOUNT_LOCKED',
                user=user,
                ip_address=client_ip,
                description=f"Account locked after {user.failed_login_attempts} failed attempts",
                severity='HIGH',
                request=request
            )
            
            logger.warning(f"Account {username} locked due to {user.failed_login_attempts} failed login attempts from IP {client_ip}")
        else:
            user.save(update_fields=['failed_login_attempts'])
    
    except User.DoesNotExist:
        user = None
        logger.warning(f"Failed login attempt for non-existent user: {username} from IP {client_ip}")
    
    # Log the failed attempt
    SecurityEvent.log_event(
        'LOGIN_FAILED',
        user=user,
        ip_address=client_ip,
        description=f"Failed login attempt for username: {username}",
        severity='MEDIUM',
        request=request,
        username=username
    )


# @receiver(pre_save)
def log_password_changes(sender, instance, **kwargs):
    """Log password change events"""
    if sender == User and instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            if old_instance.password != instance.password:
                SecurityEvent.log_event(
                    'PASSWORD_CHANGE',
                    user=instance,
                    ip_address='127.0.0.1',  # Server-side change
                    description=f"Password changed for user {instance.username}",
                    severity='MEDIUM'
                )
                
                # Update password change timestamp
                if hasattr(instance, 'last_password_change'):
                    instance.last_password_change = timezone.now()
                
                logger.info(f"Password changed for user {instance.username}")
        except User.DoesNotExist:
            pass


@receiver(post_save)
def log_model_creation(sender, instance, created, **kwargs):
    """Log creation of important models"""
    
    # Skip during migrations
    from django.conf import settings
    if getattr(settings, 'MIGRATION_MODE', False):
        return
    
    # Skip security models to avoid infinite loops
    security_models = ['SecurityEvent', 'AuditLog', 'LoginAttempt', 'RateLimitTracker']
    if sender.__name__ in security_models:
        return
    
    if created:
        # Get user from thread local or system
        user = getattr(instance, 'created_by', None)
        
        AuditLog.objects.create(
            user=user,
            action='CREATE',
            content_type=sender.__name__,
            object_id=str(instance.pk),
            object_repr=str(instance)[:200],
            ip_address='127.0.0.1',  # Server-side operation
            new_values=_get_model_fields(instance),
            additional_info={'model_name': sender.__name__}
        )


@receiver(post_save)
def log_model_updates(sender, instance, created, **kwargs):
    """Log updates to important models"""
    
    # Skip during migrations
    from django.conf import settings
    if getattr(settings, 'MIGRATION_MODE', False):
        return
    
    # Skip security models and creation events
    security_models = ['SecurityEvent', 'AuditLog', 'LoginAttempt', 'RateLimitTracker']
    if sender.__name__ in security_models or created:
        return
    
    try:
        # Get original instance to compare changes
        original = sender.objects.get(pk=instance.pk)
        changes = _get_field_changes(original, instance)
        
        if changes:
            user = getattr(instance, 'updated_by', None)
            
            AuditLog.objects.create(
                user=user,
                action='UPDATE',
                content_type=sender.__name__,
                object_id=str(instance.pk),
                object_repr=str(instance)[:200],
                ip_address='127.0.0.1',  # Server-side operation
                changes=changes,
                old_values=_get_model_fields(original),
                new_values=_get_model_fields(instance),
                additional_info={'model_name': sender.__name__}
            )
    except sender.DoesNotExist:
        pass


@receiver(post_delete)
def log_model_deletion(sender, instance, **kwargs):
    """Log deletion of important models"""
    
    # Skip security models
    security_models = ['SecurityEvent', 'AuditLog', 'LoginAttempt', 'RateLimitTracker']
    if sender.__name__ in security_models:
        return
    
    # Get user from instance if available
    user = getattr(instance, 'deleted_by', None)
    
    AuditLog.objects.create(
        user=user,
        action='DELETE',
        content_type=sender.__name__,
        object_id=str(instance.pk),
        object_repr=str(instance)[:200],
        ip_address='127.0.0.1',  # Server-side operation
        old_values=_get_model_fields(instance),
        additional_info={'model_name': sender.__name__}
    )


def _get_model_fields(instance):
    """Get all field values from a model instance"""
    fields = {}
    for field in instance._meta.fields:
        field_name = field.name
        try:
            field_value = getattr(instance, field_name)
            # Convert to string for JSON serialization
            if hasattr(field_value, 'isoformat'):  # datetime objects
                field_value = field_value.isoformat()
            elif hasattr(field_value, '__str__'):
                field_value = str(field_value)
            fields[field_name] = field_value
        except Exception:
            fields[field_name] = None
    return fields


def _get_field_changes(original, updated):
    """Compare two model instances and return changed fields"""
    changes = {}
    
    for field in original._meta.fields:
        field_name = field.name
        try:
            old_value = getattr(original, field_name)
            new_value = getattr(updated, field_name)
            
            if old_value != new_value:
                # Convert to string for JSON serialization
                if hasattr(old_value, 'isoformat'):
                    old_value = old_value.isoformat()
                elif hasattr(old_value, '__str__'):
                    old_value = str(old_value)
                
                if hasattr(new_value, 'isoformat'):
                    new_value = new_value.isoformat()
                elif hasattr(new_value, '__str__'):
                    new_value = str(new_value)
                
                changes[field_name] = {
                    'old': old_value,
                    'new': new_value
                }
        except Exception:
            continue
    
    return changes


# Custom signal for security violations
from django.dispatch import Signal

security_violation_detected = Signal()

@receiver(security_violation_detected)
def handle_security_violation(sender, violation_type, user, request, details, **kwargs):
    """Handle security violations with automated response"""
    
    client_ip = get_client_ip(request) if request else '127.0.0.1'
    
    # Log the violation
    SecurityEvent.log_event(
        'SECURITY_VIOLATION',
        user=user,
        ip_address=client_ip,
        description=f"Security violation detected: {violation_type}",
        severity='CRITICAL',
        request=request,
        violation_type=violation_type,
        details=details
    )
    
    # Automated response based on violation type
    if violation_type in ['SQL_INJECTION', 'XSS_ATTEMPT', 'DIRECTORY_TRAVERSAL']:
        # Block IP temporarily
        from django.core.cache import cache
        blocked_ips_key = 'security:blocked_ips'
        blocked_ips = cache.get(blocked_ips_key, set())
        blocked_ips.add(client_ip)
        cache.set(blocked_ips_key, blocked_ips, 3600)  # Block for 1 hour
        
        logger.critical(f"IP {client_ip} automatically blocked due to {violation_type}")
    
    elif violation_type == 'BRUTE_FORCE':
        # Lock user account if user is identified
        if user:
            user.lock_account(duration_minutes=60)
            logger.critical(f"User {user.username} account locked due to brute force attempt")
    
    # Send alert notification (implement as needed)
    _send_security_alert(violation_type, user, client_ip, details)


def _send_security_alert(violation_type, user, client_ip, details):
    """Send security alert notification"""
    # Placeholder for notification system
    # In production, this could send emails, Slack messages, etc.
    
    logger.critical(
        f"SECURITY ALERT: {violation_type} detected from IP {client_ip} "
        f"{'for user ' + user.username if user else 'for anonymous user'}"
    )