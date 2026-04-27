from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Organization, Driver
from configuration.models import PostalInfo


def auto_populate_address_from_pincode(instance, pincode_field='pincode', prefix=''):
    """
    Helper function to auto-populate address fields based on pincode

    Args:
        instance: Model instance
        pincode_field: Name of the pincode field to use
        prefix: Prefix for field names (e.g., 'family_' for family address)
    """
    pincode_value = getattr(instance, pincode_field, None)
    if pincode_value:
        try:
            pincode_int = int(pincode_value)
            details = PostalInfo.get_postal_details(pincode_int)

            if details:
                # Only update fields that are currently empty
                state_field = f"{prefix}state" if prefix else "state"
                district_field = f"{prefix}district" if prefix else "district"
                city_field = f"{prefix}city" if prefix else "city"
                locality_field = f"{prefix}locality" if prefix else "locality"

                if hasattr(instance, state_field) and not getattr(instance, state_field):
                    setattr(instance, state_field, details.get("statename"))

                if hasattr(instance, district_field) and not getattr(instance, district_field):
                    setattr(instance, district_field, details.get("Districtname"))

                if hasattr(instance, city_field) and not getattr(instance, city_field):
                    setattr(instance, city_field, details.get("Taluk"))

                if hasattr(instance, locality_field) and not getattr(instance, locality_field):
                    setattr(instance, locality_field, details.get("officename"))
        except (ValueError, TypeError):
            # Invalid pincode format, skip auto-population
            pass


@receiver(pre_save, sender=Organization)
def organization_pre_save(sender, instance, **kwargs):
    """Auto-populate Organization address fields from pincode"""
    auto_populate_address_from_pincode(instance)


@receiver(pre_save, sender=Driver)
def driver_pre_save(sender, instance, **kwargs):
    """Auto-populate Driver address and family address fields from pincode"""
    # Regular address
    auto_populate_address_from_pincode(instance)
    # Family address
    auto_populate_address_from_pincode(instance, pincode_field='family_pincode', prefix='family_')







