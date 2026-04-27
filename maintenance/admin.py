from django.contrib import admin
from django.utils.safestring import mark_safe
from .forms import MaintenanceRecordForm
from .models import MaintenanceRecord, Tyre, TyreTransaction
def _choice_label(ch):
    # Works whether your configuration.Choice uses name/value/key
    if not ch:
        return ""
    return getattr(ch, "name", None) or getattr(ch, "value", None) or getattr(ch, "key", None) or str(ch)


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    form = MaintenanceRecordForm
    # Hide the raw GFK columns (handled via performed_by_combined in the form)
    exclude = ("content_type", "object_id",)

    fieldsets = (
        ("Maintenance Details", {
            "fields": ("vehicle", "service_type", "items", "service_date", "performed_by_combined")
        }),
        ("Tyre Information", {
            "fields": ("tyre",),
            "description": 'Select tyre only when service type is "Tyre".',
            "classes": ("collapse",),
        }),
        ("Billing / Invoice", {
            "fields": ("vendors", "invoice_no", "quantity", "rate", "gst", "total_cost", "maintenance_document"),
            "description": "Vendor, pricing, taxes and final totals."
        }),
        ("Next & Notes", {
            "fields": ("next_due_date", "mileage_at_service", "next_mileage_due_date",  "notes"),
            "description": "Follow-ups and internal notes."
        }),
    )

    list_display = (
        "vehicle",
        "service_type_display",
        "tyre_display",
        "service_date",
        "next_due_date",
        "vendor_display",
        "total_cost",
        "performed_by_display",
    )
    list_filter = ("service_type", "vendors", "service_date")
    search_fields = (
        "vehicle__registration_number",
        "tyre__tyreNo",
        "invoice_no",
        "notes",
        # assuming Choice has .name; if it's .value, change accordingly
        "service_type__name",
        "vendors__name",
    )
    date_hierarchy = "service_date"
    autocomplete_fields = ("vehicle", "service_type", "items", "tyre", "vendors")
    def service_type_display(self, obj):
        return _choice_label(obj.service_type)
    service_type_display.short_description = "Service Type"

    def vendor_display(self, obj):
        return _choice_label(obj.vendors)
    vendor_display.short_description = "Vendor"

    def performed_by_display(self, obj):
        if obj.performed_by:
            # shows "Driver: John…" or "Owner: Jane…"
            model = obj.content_type.model if obj.content_type else ""
            if model == 'organization':
                return f"Owner: {obj.performed_by}"
            return f"{model.capitalize()}: {obj.performed_by}"
        return "-"
    performed_by_display.short_description = "Performed By"

    def tyre_display(self, obj):
        if obj.tyre:
            return f"{obj.tyre.tyreNo} ({obj.tyre.brand})"
        return "-"
    tyre_display.short_description = "Tyre"

    class Media:
        js = ("admin/js/maintenance_tyre_logic.js",)

    # Add a tiny inline script so the Tyre fieldset hides unless the selected option text == 'Tyre'
    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_tyre_field_js"] = mark_safe(self._tyre_toggle_script())
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_tyre_field_js"] = mark_safe(self._tyre_toggle_script())
        return super().change_view(request, object_id, form_url, extra_context)

    def _tyre_toggle_script(self):
        # Compares the SELECTED OPTION TEXT (not value), which works with FK Choice.
        return """
<script>
document.addEventListener('DOMContentLoaded', function() {
  function isTyreSelected() {
    var sel = document.getElementById('id_service_type');
    if (!sel || !sel.selectedOptions || !sel.selectedOptions.length) return false;
    var label = sel.selectedOptions[0].text || '';
    return label.trim().toLowerCase() === 'tyre'; // adjust if your label differs
  }
  function toggleTyreField() {
    var tyreRow = document.querySelector('.field-tyre');
    var tyreMileageRow = document.querySelector('.field-next_mileage_due_date');
    var fieldset = document.querySelector('fieldset:has(.field-tyre)');
    var show = isTyreSelected();
    [tyreRow, tyreMileageRow].forEach(function(el){
      if (el) el.style.display = show ? 'block' : 'none';
    });
    if (fieldset) fieldset.style.display = show ? 'block' : 'none';
    if (!show) {
      var tyreSelect = document.getElementById('id_tyre');
      if (tyreSelect) tyreSelect.value = '';
    }
  }
  var sel = document.getElementById('id_service_type');
  if (sel) {
    sel.addEventListener('change', toggleTyreField);
    toggleTyreField();
  }
});
</script>
        """

@admin.register(TyreTransaction)
class TyreTransactionAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Transaction Details', {
            'fields': ('tyre', 'vehicle', 'transaction_type', 'position', 'transaction_date'),
        }),
        ('Service Information', {
            'fields': ('performed_by',),
            'description': 'Details about who performed the transaction.'
        })
    )

    list_display = ('tyre', 'vehicle', 'transaction_type', 'transaction_date', 'performed_by')
    list_filter = ('transaction_type', 'transaction_date', 'performed_by')
    search_fields = ('tyre__tyreNo', 'vehicle__registration_number', 'performed_by')
    date_hierarchy = 'transaction_date'
    autocomplete_fields = ("vehicle",)


@admin.register(Tyre)
class TyreAdmin(admin.ModelAdmin):
    """
    Enhanced Tyre admin with comprehensive specification management.
    """
    fieldsets = (
        ('Tyre Identification', {
            'fields': ('tyreNo', ('brand',), ('model', 'size')),
            'description': 'Basic tyre identification and specifications.'
        }),
        ('Tyre Specifications', {
            'fields': (
                ('type', ),
                ('tube_type', ),
                'ply_rating'
            ),
            'description': 'Detailed tyre specifications and technical details.'
        }),
        ('Purchase Information', {
            'fields': (
                ('purchase_date', 'purchase_type'),
                ('amount', 'purchase_by')
            ),
            'description': 'Purchase details and cost information.'
        }),
        ('Documentation', {
            'fields': ('tyre_document', 'invoice_document'),
            'classes': ('collapse',),
            'description': 'Upload tyre documentation and purchase invoice.'
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System audit information.'
        })
    )

    list_display = (
        'tyreNo', 'brand', 'model', 'size', 'type', 'tube_type',
        'purchase_date', 'amount', 'current_vehicle_display'
    )
    list_filter = ('brand', 'type', 'tube_type', 'purchase_type', 'ply_rating')
    search_fields = ('tyreNo', 'brand', 'model', 'size')
    date_hierarchy = 'purchase_date'
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ("brand", "model",)

    def current_vehicle_display(self, obj):
        """Display current vehicle where tyre is installed"""
        vehicle = obj.get_current_vehicle()
        if vehicle:
            return f"{vehicle.registration_number}"
        return "Not Installed"

    current_vehicle_display.short_description = "Current Vehicle"

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     """Customize choice field dropdowns"""
    #     if db_field.name == "brand_choice":
    #         kwargs["help_text"] = "Select from predefined tyre brands"
    #     elif db_field.name == "tyre_type_choice":
    #         kwargs["help_text"] = "Select tyre type for standardization"
    #     elif db_field.name == "tube_type_choice":
    #         kwargs["help_text"] = "Select tube type"
    #     elif db_field.name == "position_choice":
    #         kwargs["help_text"] = "Select typical tyre position"
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)


    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'tube_type', 'type'
        ).prefetch_related('transactions')

