from django.contrib.auth.models import Group
from django.conf import settings

# -----------------------
# Role definitions
# -----------------------
ROLE_DRIVER = 'driver'
ROLE_TRANSPORTER = 'transporter'
ROLE_COMPANY = 'company'
ROLE_BROKER = 'broker'
ROLE_OWNER = 'owner'
ROLE_OPERATION = 'operation'
ROLE_FINANCE = 'finance'
ROLE_SUPERUSER = 'superuser'

ALL_ROLES = [
    ROLE_DRIVER,
    ROLE_TRANSPORTER,
    ROLE_COMPANY,
    ROLE_BROKER,
    ROLE_OWNER,
    ROLE_OPERATION,
    ROLE_FINANCE,
    ROLE_SUPERUSER,
]

# Approval related roles – users belonging to any of these (or superuser) can approve/deny
APPROVER_ROLES = [ROLE_FINANCE, ROLE_OWNER, ROLE_SUPERUSER]

# Common approval status values (used across multiple models)
APPROVAL_STATUS = [
    ('PENDING', 'Pending'),
    ('APPROVED', 'Approved'),
    ('DENIED', 'Denied'),
]


def ensure_role_groups_exist():
    """Create Django auth Groups for each role if they don't exist."""
    for role in ALL_ROLES:
        Group.objects.get_or_create(name=role)


def assign_role(user, role_name: str):
    """Assign a role (i.e., Django Group) to a user."""
    if role_name not in ALL_ROLES:
        raise ValueError(f"Unknown role '{role_name}'. Valid roles – {ALL_ROLES}")

    group, _ = Group.objects.get_or_create(name=role_name)
    user.groups.add(group)
    return group


def user_has_role(user, role_name: str) -> bool:
    """Check if a user belongs to a given role (or is a superuser)."""
    if role_name == ROLE_SUPERUSER:
        return user.is_superuser
    return user.is_superuser or user.groups.filter(name=role_name).exists()


def is_approver(user) -> bool:
    """Return True if the user is allowed to approve / deny expenses & advances."""
    return user.is_superuser or any(user_has_role(user, r) for r in APPROVER_ROLES)