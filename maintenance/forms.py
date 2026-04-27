from django import forms
from django.contrib.contenttypes.models import ContentType

from entity.models import Driver, Organization
from maintenance.models import MaintenanceRecord


class DriverOwnerChoiceField(forms.ChoiceField):
    """
    One dropdown for both Drivers and Owner organisations.
    Returns ('content_type_id', 'object_id') in clean().
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = [("", "---------")]

    def get_choices(self):
        choices = [("", "---------")]
        try:
            for driver in Driver.objects.all().order_by("first_name", "last_name"):
                choices.append((f"driver_{driver.id}", f"Driver: {driver}"))
            owners = Organization.objects.filter(organization_type__internal_value='OWNER').order_by("organization_name")
            for owner in owners:
                choices.append((f"owner_{owner.id}", f"Owner: {owner.organization_name}"))
        except Exception:
            pass
        return choices

    def clean(self, value):
        if not value:
            return None
        try:
            if value.startswith("driver_"):
                pk = int(value.replace("driver_", ""))
                if not Driver.objects.filter(id=pk).exists():
                    raise forms.ValidationError("Selected driver does not exist")
                ct = ContentType.objects.get_for_model(Driver)
                return (ct.id, pk)
            if value.startswith("owner_"):
                pk = int(value.replace("owner_", ""))
                if not Organization.objects.filter(id=pk, organization_type__internal_value='OWNER').exists():
                    raise forms.ValidationError("Selected owner organization does not exist")
                ct = ContentType.objects.get_for_model(Organization)
                return (ct.id, pk)
            raise forms.ValidationError("Invalid selection format")
        except ValueError:
            raise forms.ValidationError("Invalid ID format")


class MaintenanceRecordForm(forms.ModelForm):
    """
    Maintenance form aligned with the model, including a combined Driver/Owner selector.
    """
    performed_by_combined = DriverOwnerChoiceField(
        label="Performed By (Driver/Owner Organization)",
        required=False,
        help_text="Select either a driver or owner for this record"
    )

    class Meta:
        model = MaintenanceRecord
        fields = [
            "vehicle",
            "service_type",
            "items",
            "service_date",
            "next_due_date",
            "mileage_at_service",
            "tyre",
            "next_mileage_due_date",
            "vendors",
            "invoice_no",
            "quantity",
            "rate",
            "gst",
            "total_cost",
            "notes",
            "maintenance_document",
        ]
        widgets = {
            "service_date": forms.DateInput(attrs={"type": "date"}),
            "next_due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields["performed_by_combined"].choices = (
                self.fields["performed_by_combined"].get_choices()
            )
        except Exception:
            self.fields["performed_by_combined"].choices = [("", "---------")]

        # Pre-populate combined field when editing
        inst = self.instance
        if inst and inst.pk and inst.content_type_id and inst.object_id:
            model = inst.content_type.model
            if model == "driver":
                self.fields["performed_by_combined"].initial = f"driver_{inst.object_id}"
            elif model == "organization":
                self.fields["performed_by_combined"].initial = f"owner_{inst.object_id}"

    def clean(self):
        cleaned = super().clean()
        combined = cleaned.get("performed_by_combined")
        if combined:
            ct_id, obj_id = combined
            cleaned["content_type"] = ContentType.objects.get(id=ct_id)
            cleaned["object_id"] = obj_id
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        combined = self.cleaned_data.get("performed_by_combined")
        if combined:
            ct_id, obj_id = combined
            instance.content_type_id = ct_id
            instance.object_id = obj_id
        else:
            instance.content_type_id = None
            instance.object_id = None
        if commit:
            instance.save()
        return instance
