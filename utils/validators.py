import os
import re
from datetime import date
from datetime import datetime
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator




#  Indian Mobile Number (starts with 6–9, 10 digits only)
indian_phone_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message="Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9."
)

#  PAN Card Validator (Format: ABCDE1234F)
def pan_validator(value):
    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', value):
        raise ValidationError("PAN must be in format 'ABCDE1234F'.")

#  Aadhaar Number Validator (12 digits)
def aadhaar_validator(value):
    if not re.match(r'^\d{12}$', value):
        raise ValidationError("Aadhaar must be a 12-digit number.")

#  Aadhaar Number Validator (12 digits)

def gst_validator(value):
    pattern = r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$'
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid 15-character GSTIN.")

def vehicle_validator(value):
    if not re.fullmatch(r'^[A-Z]{2}\d{2}[A-Z]{2}\d{3}$', value):
        raise ValidationError("Vehicle number must be in format 'KA01AB1234'.")

#  Indian License Format (e.g., MH-14-2023-1234567)
def indian_license_validator(value):
    pattern = r'^[A-Z]{2}-\d{2}-\d{4}-\d{7}$'
    if not re.match(pattern, value):
        raise ValidationError("License must be in format 'MH-14-2023-1234567'.")

#  Birthdate Validation: Must not be in future
def birthdate_validator(value):
    if value > date.today():
        raise ValidationError("Birthdate cannot be in the future.")
    
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 18:
        raise ValidationError("Age must be at least 18 years.")

#  Age Restriction: Must be at least 18 years
def age_validator(value):
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 18:
        raise ValidationError("Age must be at least 18 years.")

#  File Type Check: Only PDF, JPG, PNG allowed
def document_file_validator(value):
    ext = os.path.splitext(value.name)[1].lower()
    allowed = ['.pdf', '.jpg', '.jpeg', '.png']
    if ext not in allowed:
        raise ValidationError("Allowed file types are: PDF, JPG, JPEG, PNG.")

#  Name Check: No digits allowed
def name_no_digits_validator(value):
    if any(char.isdigit() for char in value):
        raise ValidationError("Name should not contain digits.")

#  Pincode Validation: Must be 6 digits (India-specific)
def pincode_validator(value):
    if not re.match(r'^\d{6}$', value):
        raise ValidationError("Pincode must be a 6-digit number.")

#  Cannot be empty or contain only whitespace
def non_empty_text_validator(value):
    if not value.strip():
        raise ValidationError("This field cannot be empty or contain only whitespace.")




#  Dynamic file renaming and folder structure
def user_document_upload_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    app_level, model_name = instance._meta.label.split(".")[0], instance._meta.label.split(".")[1]

    doc_type = "document"
    # Try to detect which field is currently being uploaded
    for field in instance._meta.fields:
        if hasattr(field, 'upload_to') and getattr(instance, field.name) and filename in str(getattr(instance, field.name)):
            doc_type = field.name
            break

    new_filename = f"{doc_type}_{timestamp}.{ext}"
    folder = f"files/{app_level}/{model_name}/{doc_type}/"
    return os.path.join(folder, new_filename)

def joining_date_validator(value):
    from django.utils import timezone
    if value.year < 2000 or value > timezone.now().date():
        raise ValidationError("Joining date must be between 2000 and today.")

def future_date_validator(value):
    today = date.today()
    if value <= today:
        raise ValidationError("Date must be in the future.")

# Banking-related validators

def ifsc_validator(value):
    """Validate Indian IFSC code format (e.g., SBIN0000123)"""
    pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
    if not re.match(pattern, value):
        raise ValidationError("IFSC code must be in format 'SBIN0000123' (4 letters, 1 zero, 6 alphanumeric).")

def bank_account_validator(value):
    """Validate bank account number (9-18 digits)"""
    if not re.match(r'^\d{9,18}$', value):
        raise ValidationError("Bank account number must be 9-18 digits.")

def upi_validator(value):
    """Validate UPI ID format (e.g., user@bank or user@okaxis)"""
    pattern = r'^[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+$'
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid UPI ID in format 'user@bank'.")