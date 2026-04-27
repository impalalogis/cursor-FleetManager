"""
Security utility functions for FleetManager application

Provides utility functions for:
- IP address detection
- Request sanitization
- Suspicious activity detection
- Security validation
- Encryption/decryption utilities
"""

import re
import html
import logging
from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from typing import Optional, Dict, Any, List
import ipaddress

logger = logging.getLogger('security')


def get_client_ip(request) -> str:
    """
    Get the real client IP address from request headers.
    Handles various proxy scenarios and load balancers.
    """
    # Check for forwarded headers (common with load balancers)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the chain (original client)
        ip = x_forwarded_for.split(',')[0].strip()
        if is_valid_ip(ip):
            return ip
    
    # Check other common proxy headers
    proxy_headers = [
        'HTTP_X_REAL_IP',
        'HTTP_X_CLIENT_IP',
        'HTTP_CF_CONNECTING_IP',  # Cloudflare
        'HTTP_X_CLUSTER_CLIENT_IP',
    ]
    
    for header in proxy_headers:
        ip = request.META.get(header)
        if ip and is_valid_ip(ip):
            return ip
    
    # Fall back to remote address
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def is_valid_ip(ip_string: str) -> bool:
    """
    Validate if string is a valid IP address (IPv4 or IPv6)
    """
    try:
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False


def is_private_ip(ip_string: str) -> bool:
    """
    Check if IP address is in private range
    """
    try:
        ip = ipaddress.ip_address(ip_string)
        return ip.is_private
    except ValueError:
        return False


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing/escaping dangerous characters
    """
    if not isinstance(value, str):
        value = force_str(value)
    
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]
    
    # HTML escape
    value = html.escape(value)
    
    # Remove potentially dangerous characters/patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'eval\s*\(',
        r'document\.cookie',
        r'window\.location',
    ]
    
    for pattern in dangerous_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
    
    return value.strip()


def sanitize_request_data(request):
    """
    Sanitize request data (GET, POST parameters)
    """
    # Sanitize GET parameters
    if hasattr(request, 'GET'):
        sanitized_get = {}
        for key, value in request.GET.items():
            sanitized_key = sanitize_string(key, 100)
            if isinstance(value, list):
                sanitized_value = [sanitize_string(v, 1000) for v in value]
            else:
                sanitized_value = sanitize_string(value, 1000)
            sanitized_get[sanitized_key] = sanitized_value
        request.GET = request.GET.__class__(sanitized_get)
    
    # Sanitize POST parameters
    if hasattr(request, 'POST'):
        sanitized_post = {}
        for key, value in request.POST.items():
            sanitized_key = sanitize_string(key, 100)
            if isinstance(value, list):
                sanitized_value = [sanitize_string(v, 1000) for v in value]
            else:
                sanitized_value = sanitize_string(value, 1000)
            sanitized_post[sanitized_key] = sanitized_value
        request.POST = request.POST.__class__(sanitized_post)
    
    return request


def is_suspicious_request(request, suspicious_patterns: List[str]) -> bool:
    """
    Check if request contains suspicious patterns that might indicate an attack
    """
    # Check URL path
    path = request.path.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, path, re.IGNORECASE):
            logger.warning(f"Suspicious pattern '{pattern}' found in path: {path}")
            return True
    
    # Check query parameters
    query_string = request.META.get('QUERY_STRING', '')
    for pattern in suspicious_patterns:
        if re.search(pattern, query_string, re.IGNORECASE):
            logger.warning(f"Suspicious pattern '{pattern}' found in query: {query_string}")
            return True
    
    # Check POST data
    if hasattr(request, 'POST'):
        for key, value in request.POST.items():
            combined_data = f"{key} {value}".lower()
            for pattern in suspicious_patterns:
                if re.search(pattern, combined_data, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern '{pattern}' found in POST data")
                    return True
    
    # Check headers for suspicious patterns
    suspicious_headers = [
        'HTTP_USER_AGENT',
        'HTTP_REFERER',
        'HTTP_X_FORWARDED_FOR',
    ]
    
    for header in suspicious_headers:
        header_value = request.META.get(header, '').lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, header_value, re.IGNORECASE):
                logger.warning(f"Suspicious pattern '{pattern}' found in header {header}")
                return True
    
    return False


def validate_file_upload(file_obj, allowed_extensions: List[str], max_size: int = 5242880) -> bool:
    """
    Validate uploaded file for security
    
    Args:
        file_obj: Django UploadedFile object
        allowed_extensions: List of allowed file extensions
        max_size: Maximum file size in bytes (default: 5MB)
    
    Returns:
        bool: True if file is valid, False otherwise
    """
    if not file_obj:
        return False
    
    # Check file size
    if file_obj.size > max_size:
        logger.warning(f"File upload rejected: size {file_obj.size} exceeds limit {max_size}")
        return False
    
    # Check file extension
    file_name = file_obj.name.lower()
    file_extension = file_name.split('.')[-1] if '.' in file_name else ''
    
    if file_extension not in [ext.lower() for ext in allowed_extensions]:
        logger.warning(f"File upload rejected: extension '{file_extension}' not in allowed list")
        return False
    
    # Check for double extensions (e.g., file.php.jpg)
    if file_name.count('.') > 1:
        logger.warning(f"File upload rejected: multiple extensions in filename '{file_name}'")
        return False
    
    # Basic content type validation
    dangerous_content_types = [
        'application/x-httpd-php',
        'application/x-httpd-php-source',
        'application/x-php',
        'text/x-php',
        'application/x-sh',
        'application/x-csh',
    ]
    
    if file_obj.content_type in dangerous_content_types:
        logger.warning(f"File upload rejected: dangerous content type '{file_obj.content_type}'")
        return False
    
    return True


def hash_password(password: str) -> str:
    """
    Hash password using Django's built-in password hashing
    """
    from django.contrib.auth.hashers import make_password
    return make_password(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    """
    from django.contrib.auth.hashers import check_password
    return check_password(password, hashed_password)


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def encrypt_sensitive_data(data: str, key: Optional[str] = None) -> str:
    """
    Encrypt sensitive data using Fernet encryption
    """
    from cryptography.fernet import Fernet
    from django.conf import settings
    
    if key is None:
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            # Generate a key for development (not recommended for production)
            key = Fernet.generate_key()
    
    if isinstance(key, str):
        key = key.encode()
    
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(data.encode())
    return encrypted_data.decode()


def decrypt_sensitive_data(encrypted_data: str, key: Optional[str] = None) -> str:
    """
    Decrypt sensitive data using Fernet encryption
    """
    from cryptography.fernet import Fernet
    from django.conf import settings
    
    if key is None:
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            raise ValueError("Encryption key not found in settings")
    
    if isinstance(key, str):
        key = key.encode()
    
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data.encode())
    return decrypted_data.decode()


def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """
    Mask sensitive data for display purposes
    
    Args:
        data: The sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at the end
    
    Returns:
        str: Masked data
    """
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    masked_length = len(data) - visible_chars
    return mask_char * masked_length + data[-visible_chars:]


def validate_ip_whitelist(ip_address: str, whitelist: List[str]) -> bool:
    """
    Check if IP address is in whitelist
    
    Args:
        ip_address: IP address to check
        whitelist: List of allowed IP addresses or CIDR ranges
    
    Returns:
        bool: True if IP is allowed, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_address)
        
        for allowed in whitelist:
            try:
                # Check if it's a network range
                if '/' in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if ip in network:
                        return True
                else:
                    # Check exact IP match
                    if ip == ipaddress.ip_address(allowed):
                        return True
            except ValueError:
                continue
        
        return False
    except ValueError:
        return False


def get_geolocation_info(ip_address: str) -> Dict[str, Any]:
    """
    Get geolocation information for IP address
    (This is a placeholder - you'd integrate with a real geolocation service)
    
    Args:
        ip_address: IP address to lookup
    
    Returns:
        dict: Geolocation information
    """
    # Placeholder implementation
    # In production, you'd integrate with services like MaxMind GeoIP2, IPStack, etc.
    
    if is_private_ip(ip_address):
        return {
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'is_private': True,
            'risk_score': 0,
        }
    
    return {
        'country': 'Unknown',
        'region': 'Unknown',
        'city': 'Unknown',
        'is_private': False,
        'risk_score': 1,  # Unknown IPs get low risk score
    }


def calculate_risk_score(request, user=None) -> int:
    """
    Calculate risk score for a request
    
    Args:
        request: Django request object
        user: User object (if authenticated)
    
    Returns:
        int: Risk score (0-100, higher is more risky)
    """
    risk_score = 0
    
    client_ip = get_client_ip(request)
    
    # IP-based risk factors
    if is_private_ip(client_ip):
        risk_score += 5  # Private IPs are generally safer
    else:
        risk_score += 10  # Public IPs have higher base risk
    
    # User agent analysis
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    suspicious_ua_patterns = ['bot', 'crawler', 'scanner', 'hack', 'exploit']
    
    for pattern in suspicious_ua_patterns:
        if pattern in user_agent:
            risk_score += 20
            break
    
    # Check for common attack patterns in request
    if is_suspicious_request(request, [
        r'<script', r'javascript:', r'union.*select', r'drop.*table'
    ]):
        risk_score += 50
    
    # Time-based factors (requests outside business hours)
    from django.utils import timezone
    current_hour = timezone.now().hour
    if current_hour < 6 or current_hour > 22:  # Outside 6 AM - 10 PM
        risk_score += 5
    
    # User-specific factors
    if user and user.is_authenticated:
        risk_score -= 10  # Authenticated users have lower risk
        
        if hasattr(user, 'failed_login_attempts') and user.failed_login_attempts > 3:
            risk_score += 15
    else:
        risk_score += 15  # Anonymous users have higher risk
    
    return min(risk_score, 100)  # Cap at 100