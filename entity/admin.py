from django.contrib import admin
from entity.models import (
    Driver,
    Vehicle,
    Organization,
    VehicleDocument,
    DriverDocument,
    OrganizationDocument,
)
from operations.models import DriverAdvance, ShipmentExpense
from maintenance.models import MaintenanceRecord, TyreTransaction
from django.utils.html import format_html

class DriverAdvanceInline(admin.TabularInline):
    model = DriverAdvance
    extra = 0
    readonly_fields = ('amount', 'date', 'description')


class ShipmentExpenseInline(admin.TabularInline):
    model = ShipmentExpense
    extra = 0
    readonly_fields = ('amount', 'shipment', 'description')

    # Note: ShipmentExpense uses GenericForeignKey, so this inline should only show
    # expenses where the Driver is the expense_by target

    def get_queryset(self, request):
        """Filter to show only expenses made by the current driver"""
        qs = super().get_queryset(request)
        # Get ContentType for Driver model
        from django.contrib.contenttypes.models import ContentType
        driver_ct = ContentType.objects.get_for_model(Driver)
        qs = qs.filter(content_type=driver_ct)

        # In Driver change view, scope inline rows to this specific driver.
        object_id = getattr(getattr(request, "resolver_match", None), "kwargs", {}).get("object_id")
        if object_id:
            qs = qs.filter(object_id=object_id)
        return qs

    def has_add_permission(self, request, obj=None):
        """Disable adding new expenses through this inline to avoid confusion"""
        return False


class DriverDocumentInline(admin.TabularInline):
    model = DriverDocument
    extra = 0
    fields = ('doc_type', 'file', 'issue_date', 'expiry_date', 'doc_no', 'download_link', 'uploaded_at')
    readonly_fields = ('download_link', 'uploaded_at')
    ordering = ('-uploaded_at',)

    def download_link(self, obj):
        if obj and obj.file:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.file.url)
        return "-"
    download_link.short_description = "File"


class OrganizationDocumentInline(admin.TabularInline):
    model = OrganizationDocument
    extra = 0
    fields = ('doc_type', 'file', 'issue_date', 'expiry_date', 'doc_no', 'notes', 'download_link', 'uploaded_at')
    readonly_fields = ('download_link', 'uploaded_at')
    ordering = ('-uploaded_at',)

    def download_link(self, obj):
        if obj and obj.file:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.file.url)
        return "-"

    download_link.short_description = "File"

@admin.register(DriverDocument)
class DriverDocumentAdmin(admin.ModelAdmin):
    list_display = ('driver', 'doc_type', 'expiry_date', 'uploaded_at', 'file_link')
    list_filter = ('doc_type', 'uploaded_at', 'expiry_date', 'driver')
    search_fields = ('driver__first_name', 'driver__last_name', 'driver__license_number')
    date_hierarchy = 'uploaded_at'
    readonly_fields = ('uploaded_at',)
    autocomplete_fields = ("driver",)

    def file_link(self, obj):
        return format_html('<a href="{}" target="_blank">Open</a>', obj.file.url) if obj.file else "-"
    file_link.short_description = "File"

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'title', 'first_name', 'middle_name', 'last_name',
                'date_of_birth', 'gender', 'age', 'is_active'
            )
        }),
        ('Organization & Contact', {
            'fields': (
                'owner', 'phone_number', 'email', 'contact_person', 'contact_phone', 'contact_email'
            )
        }),

        ('Current Address', {
            'fields': (
                'address_line_1', 'address_line_2', 'landmark',
                'pincode', 'city', 'locality', 'district', 'state', 'country'
            ),
            'classes': ('collapse',)
        }),
        ('Family Address', {
            'fields': (
                'family_name', 'family_address_line_1', 'family_address_line_2',
                'family_locality', 'family_city', 'family_district', 'family_state',
                'family_country', 'family_pincode', 'family_landmark', 'family_phone_number'
            ),
            'classes': ('collapse',)
        }),
        # ('Financial Summary', {
        #     'fields': (
        #         'advance_breakdown_display', 'expense_breakdown_display', 'financial_summary_display'
        #     ),
        #     'classes': ('collapse',)
        # })
    )

    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     # if coming from autocomplete request, still show only active
    #     if request.path.endswith("/autocomplete/"):
    #         return qs.filter(is_active=True)
    #     return qs
    search_fields = ('first_name', 'last_name', 'license_number')
    list_display = (
        'first_name', 'last_name', 'owner',
        'phone_number')  # 'total_advances', 'total_expenses', 'current_balance', 'unsettled_balance',

    list_filter = ('gender', 'owner')
    readonly_fields = ('age', 'locality', 'district', 'state', 'country', 'city')
    inlines = [DriverDocumentInline]
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Organization Information', {
            'fields': (
                'organization_number','organization_name', 'organization_type', 'location','GST_NO', 'GST_document',

            )
        }),
        (' Contact Details', {
            'fields': (
                'phone_number', 'email', 'contact_person', 'contact_phone', 'contact_email'
            ),
            'classes': ('collapse',)
        }),
        ('Address Information', {
            'fields': (
                'address_line_1', 'address_line_2', 'landmark',
                'pincode', 'city', 'locality', 'district', 'state', 'country'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )

    list_display = (
        'organization_name', 'organization_type', 'GST_NO',
    )

    list_filter = ('organization_type',)
    search_fields = ('organization_name', 'GST_NO', 'location__name')
    readonly_fields = ('locality', 'district', 'state', 'country', 'city','organization_number')
    inlines = [OrganizationDocumentInline]
    autocomplete_fields = ("location",)
@admin.register(OrganizationDocument)
class OrganizationDocumentAdmin(admin.ModelAdmin):
    list_display = ('organization', 'doc_type', 'expiry_date', 'uploaded_at', 'file_link')
    list_filter = ('doc_type', 'uploaded_at', 'expiry_date', 'organization')
    search_fields = ('organization__organization_name', 'doc_no')
    date_hierarchy = 'uploaded_at'
    readonly_fields = ('uploaded_at',)
    autocomplete_fields = ("organization", )

    def file_link(self, obj):
        return format_html('<a href="{}" target="_blank">Open</a>', obj.file.url) if obj.file else "-"

    file_link.short_description = "File"

    # Add banking details filter for organizations
    # filter_horizontal = ('banking_details',)

    # def get_banking_details_count(self, obj):
    #     """Display count of linked banking details"""
    #     return obj.banking_details.count()
    # get_banking_details_count.short_description = "Banking Accounts"

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     """Filter primary banking detail to only show linked accounts"""
    #
    #     if db_field.name == "primary_banking_detail":
    #         organization = getattr(request, "_obj_", None)
    #         if organization is not None:
    #             kwargs["queryset"] = organization.banking_details.all()
    #         else:
    #             kwargs["queryset"] = BankingDetail.objects.none()
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # def get_form(self, request, obj=None, **kwargs):
    #     # Store the object in the request for use in formfield_for_foreignkey
    #     request._obj_ = obj
    #     return super().get_form(request, obj, **kwargs)


class MaintenanceInline(admin.TabularInline):
    model = MaintenanceRecord
    extra = 1


class TyreInline(admin.TabularInline):  # or StackedInline
    model = TyreTransaction
    extra = 1  # Number of tyres to show by default


class VehicleDocumentInline(admin.TabularInline):
    model = VehicleDocument
    extra = 0
    fields = ('doc_type', 'file', 'issue_date', 'expiry_date', 'notes', 'download_link', 'uploaded_at')
    readonly_fields = ('download_link', 'uploaded_at')
    ordering = ('-uploaded_at',)
    autocomplete_fields = ("vehicle", )

    def download_link(self, obj):
        if obj and obj.file:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.file.url)
        return "-"
    download_link.short_description = "File"

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Vehicle Identification', {
            'fields': ('registration_number', 'chassis_number', 'brand_name',),
            'description': 'Basic vehicle identification and specifications.'
        }),
        ('Ownership', {
            'fields': ('owner', 'is_active'),
            'description': 'Vehicle ownership and operational status.'
        }),
        ('Vehicle Specifications', {
            'fields': (
                'model_name', 'truck_type', 'engine_type',
                'fuel_type', 'body_type', 'truck_specification', 'wheel_count', 'load_capacity_tons'
            ),
            'classes': ('collapse',),
        }),
        ('Compliance & Certificates (Expiry Dates)', {
            'fields': (
                'insurance_expiry', 'fitness_certificate_expiry',
                'pollution_certificate_expiry', 'maintenance_due_date'
            ),
            'classes': ('collapse',),
            'description': 'Upload actual files below in the Documents section.'
        }),
    )

    inlines = [VehicleDocumentInline]  # 👈 enables multiple docs per vehicle
    list_display = ('registration_number', 'brand_name', 'model_name', 'truck_type', 'owner', 'is_active')
    list_filter = ('brand_name', 'truck_type', 'fuel_type', 'is_active', 'owner')
    search_fields = ('registration_number', 'brand_name__name', 'model_name__name')  # adjust if Choice uses .value/.key
    date_hierarchy = 'maintenance_due_date'


# Optional: a standalone admin for documents
@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'doc_type', 'expiry_date', 'uploaded_at', 'file_link')
    list_filter = ('doc_type', 'uploaded_at', 'expiry_date')
    search_fields = ('vehicle__registration_number',)
    date_hierarchy = 'uploaded_at'
    readonly_fields = ('uploaded_at',)

    def file_link(self, obj):
        return format_html('<a href="{}" target="_blank">Open</a>', obj.file.url) if obj.file else "-"
    file_link.short_description = "File"