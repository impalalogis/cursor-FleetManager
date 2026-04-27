# operations/forms.py
from django import forms
from .models import ShipmentExpense
from django.contrib.contenttypes.models import ContentType
from entity.models import Organization, Driver
from operations.models import Shipment
from .models import DriverAdvance

class DriverOwnerChoiceField(forms.ChoiceField):
    """
    Custom field that provides a single dropdown containing both drivers and owner organisations.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don't set choices during init to avoid database queries during module import
        self.choices = [('', '---------')]
    
    def get_choices(self):
        """
        Generate choices combining drivers and owner organisations.
        Format: [('driver_<id>', 'Driver: Name'), ('owner_<id>', 'Owner: Organisation')]
        """
        choices = [('', '---------')]  # Empty choice
        
        try:
            # Get all drivers
            for driver in Driver.objects.all().order_by('first_name', 'last_name'):
                choices.append((f'driver_{driver.id}', f'Driver: {driver}'))

            # Get all owner organizations
            owners = Organization.objects.filter(organization_type__internal_value='OWNER').order_by('organization_name')
            for owner in owners:
                choices.append((f'owner_{owner.id}', f'Owner: {owner.organization_name}'))
        except Exception:
            # If database is not available, return empty choices
            pass
        
        return choices
    
    def clean(self, value):
        """
        Convert the choice value back to a tuple of (content_type_id, object_id)
        """
        if not value:
            return None
            
        try:
            if value.startswith('driver_'):
                driver_id = int(value.replace('driver_', ''))
                # Verify the driver exists
                if not Driver.objects.filter(id=driver_id).exists():
                    raise forms.ValidationError("Selected driver does not exist")
                driver_ct = ContentType.objects.get_for_model(Driver)
                return (driver_ct.id, driver_id)
            elif value.startswith('owner_'):
                owner_id = int(value.replace('owner_', ''))
                # Verify the owner organization exists
                owner_qs = Organization.objects.filter(id=owner_id, organization_type__internal_value='OWNER')
                if not owner_qs.exists():
                    raise forms.ValidationError("Selected owner organization does not exist")
                owner_ct = ContentType.objects.get_for_model(Organization)
                return (owner_ct.id, owner_id)
            else:
                raise forms.ValidationError("Invalid selection format")
        except ValueError:
            raise forms.ValidationError("Invalid ID format")
        except Exception as e:
            raise forms.ValidationError(f"Error processing selection: {str(e)}")


class ShipmentExpenseForm(forms.ModelForm):
    """
    Form for ShipmentExpense with a combined driver/owner dropdown.
    """
    
    expense_by_combined = DriverOwnerChoiceField(
        label="Expense By (Driver/Owner Organization)",
        required=False,
        help_text="Select either a driver or owner for this expense"
    )

    class Meta:
        model = ShipmentExpense
        fields = ['shipment', 'expense_type', 'amount', 'expense_date', 'description']
        widgets = {
            "expense_by_combined": forms.Select(),
            'expense_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["expense_by_combined"].widget = ExpenseBySelect2Widget(
            url=reverse("expense_by_autocomplete")
        )
        # Update the custom field choices when form is actually instantiated
        try:
            self.fields['expense_by_combined'].choices = self.fields['expense_by_combined'].get_choices()
        except Exception:
            # If database is not available, keep empty choices
            self.fields['expense_by_combined'].choices = [('', '---------')]
        
        # If editing an existing instance, pre-populate the combined field
        if self.instance and self.instance.pk and self.instance.content_type and self.instance.object_id:
            if self.instance.content_type.model == 'driver':
                self.fields['expense_by_combined'].initial = f'driver_{self.instance.object_id}'
            elif self.instance.content_type.model == 'organization':
                self.fields['expense_by_combined'].initial = f'owner_{self.instance.object_id}'


    def clean(self):
        cleaned_data = super().clean()
        expense_by_combined = cleaned_data.get('expense_by_combined')
        
        if expense_by_combined:
            content_type_id, object_id = expense_by_combined
            cleaned_data['content_type'] = ContentType.objects.get(id=content_type_id)
            cleaned_data['object_id'] = object_id
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the content_type and object_id based on the combined field
        expense_by_combined = self.cleaned_data.get('expense_by_combined')
        if expense_by_combined:
            content_type_id, object_id = expense_by_combined
            instance.content_type_id = content_type_id
            instance.object_id = object_id
        else:
            # Clear the GenericForeignKey if no selection
            instance.content_type_id = None
            instance.object_id = None
        
        if commit:
            instance.save()
        return instance

# forms.py
from django import forms
from django.contrib.contenttypes.models import ContentType
from entity.models import Organization
from operations.models import ShipmentExpense  # only if needed elsewhere
from .models import DriverAdvance

class DriverAdvanceAdminForm(forms.ModelForm):
    RELATED_CHOICES = (
        ('', '— Select type —'),
        ('owner', 'Owner Organization'),
        ('shipment', 'Shipment (Operations)'),
    )

    related_type = forms.ChoiceField(
        choices=RELATED_CHOICES, required=False, label='Advance By Type'
    )
    owner_ref = forms.ModelChoiceField(
        queryset=Organization.objects.filter(organization_type__internal_value='OWNER'), required=False, label='Owner'
    )
    # NOTE: we do NOT add a second shipment field.
    # We will reuse the model field `shipment` for both payer & “for” shipment.

    class Meta:
        model = DriverAdvance
        fields = '__all__'   # includes model's `shipment`
        widgets = {
            # let admin supply autocomplete for shipment (see admin.py)
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        inst = self.instance
        # Pre-fill related_type + owner_ref from existing content_type/object_id
        if inst and inst.pk and inst.content_type_id and inst.object_id:
            app_label = inst.content_type.app_label
            model = inst.content_type.model
            if (app_label, model) == ('entity', 'organization'):
                self.fields['related_type'].initial = 'owner'
                try:
                    self.fields['owner_ref'].initial = Organization.objects.only('id').get(pk=inst.object_id)
                except Organization.DoesNotExist:
                    pass
            elif (app_label, model) == ('operations', 'shipment'):
                self.fields['related_type'].initial = 'shipment'
                # we’ll use the model `shipment` field directly, so nothing else here

        # If payer is shipment and instance has shipment set, that’s already visible in the
        # model’s `shipment` field.

    def clean(self):
        cleaned = super().clean()
        rtype = cleaned.get('related_type')
        owner_ref = cleaned.get('owner_ref')
        shipment = cleaned.get('shipment')

        # Default: clear GFK
        self.instance.content_type = None
        self.instance.object_id = None

        if rtype == 'owner':
            if not owner_ref:
                raise forms.ValidationError("Please select an Owner organization for 'Advance By'.")
            if getattr(owner_ref, 'organization_type_code', None) != 'OWNER':
                raise forms.ValidationError("Selected organization must be of type OWNER.")
            ct = ContentType.objects.get(app_label='entity', model='organization')
            self.instance.content_type_id = ct.id
            self.instance.object_id = owner_ref.pk
            # shipment remains whatever user chose (optional)

        elif rtype == 'shipment':
            # Use the ONE shipment field for both payer & “for” shipment
            if not shipment:
                raise forms.ValidationError("Please select a Shipment to act as payer.")
            ct = ContentType.objects.get(app_label='operations', model='shipment')
            self.instance.content_type_id = ct.id
            self.instance.object_id = shipment.pk
            # ensure model.shipment matches payer shipment (soft sync)
            self.instance.shipment_id = shipment.pk

        else:
            # no payer chosen: allow content_type/object_id to remain null
            pass

        return cleaned



from django import forms
from django.urls import reverse

class ExpenseBySelect2Widget(forms.Select):
    class Media:
        css = {"all": ("admin/css/vendor/select2/select2.css",)}
        js = (
            "admin/js/vendor/jquery/jquery.js",
            "admin/js/vendor/select2/select2.full.js",
            "admin/js/jquery.init.js",
            "operations/js/expense_by_select2.js",
        )

    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop("url")
        super().__init__(*args, **kwargs)

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs["data-ajax--url"] = self.url
        return attrs
