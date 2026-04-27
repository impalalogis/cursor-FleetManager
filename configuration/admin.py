from django.contrib import admin
from .models import Location, Route, BankingDetail, Choice


# Register your models here.
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('source', 'destination', 'via')
    search_fields = ('source', 'destination', 'via')


@admin.register(BankingDetail)
class BankingDetailAdmin(admin.ModelAdmin):
    list_display = (
        'account_holder_name',
        'bank_name',
        'get_masked_account_number',
        'account_type',
        # 'status',
        # 'verification_status',
        # 'is_primary',
        # 'get_linked_entities_count',
        # 'get_primary_entity_display'
    )
    list_filter = (
        'account_type',
        # 'status',
        # 'verification_status',
        # 'is_primary',
        # 'is_enabled_for_auto_transfer'
    )
    search_fields = (
        'account_holder_name',
        'bank_name',
        'account_number',
        'ifsc_code',
        # 'upi_id',
        'branch_name'
    )
    readonly_fields = (
        # 'get_masked_account_number',
        # 'get_linked_entities_display',
        # 'get_primary_entity_display',
        # 'get_linked_entities_count',
        'branch_name',
    )

    fieldsets = (
        ('Basic Account Information', {
            'fields': (
                'account_holder_name',
                'bank_name',
                'account_number',
                'account_type'
            )
        }),
        # ('Entity Relationships', {
        #     'fields': (
        #         'get_linked_entities_display',
        #         'get_primary_entity_display',
        #         'get_linked_entities_count'
        #     ),
        #     'description': 'Shows which entities (drivers, brokers, etc.) are linked to this banking detail'
        # }),
        ('Indian Banking Details', {
            'fields': (
                'ifsc_code',
                'branch_name',
                'branch_address',
                'branch_city',
                'branch_state',
                'branch_pincode'
            )
        }),
        # ('Digital Payment Options', {
        #     'fields': (
        #         'upi_id',
        #         'mobile_number'
        #     )
        # }),
        # ('Online Banking Credentials', {
        #     'fields': (
        #         'customer_id',
        #         'user_id'
        #     ),
        #     'classes': ('collapse',)
        # }),
        # ('Status and Verification', {
        #     'fields': (
        #         'status',
        #         'verification_status',
        #         'verification_date'
        #     )
        # }),
        # ('Configuration', {
        #     'fields': (
        #         'is_primary',
        #         'is_enabled_for_auto_transfer',
        #         'daily_transaction_limit',
        #         'monthly_transaction_limit'
        #     )
        # }),
        # ('API Integration', {
        #     'fields': (
        #         'api_key',
        #         'api_secret',
        #         'last_sync_datetime'
        #     ),
        #     'classes': ('collapse',)
        # }),
        # ('Audit Information', {
        #     'fields': (
        #         'created_at',
        #         'updated_at',
        #         'created_by',
        #         'updated_by',
        #         'notes'
        #     ),
        #     'classes': ('collapse',)
        # })
    )

    actions = ['mark_as_verified', 'mark_as_primary', 'enable_auto_transfer']

    # def get_linked_entities_count(self, obj):
    #     """Display count of linked entities"""
    #     entities = obj.get_linked_entities()
    #     return len(entities)
    # get_linked_entities_count.short_description = "Linked Entities"

    def get_linked_entities_display(self, obj):
        """Display linked entities in admin"""
        return obj.get_linked_entities_display()

    get_linked_entities_display.short_description = "Linked Entities"

    def get_primary_entity_display(self, obj):
        """Display primary entity in admin"""
        return obj.get_primary_entity_display()

    get_primary_entity_display.short_description = "Primary For"

    def mark_as_verified(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            verification_status='VERIFIED',
            verification_date=timezone.now(),
            status='ACTIVE'
        )
        self.message_user(request, f"{updated} banking details marked as verified.")

    mark_as_verified.short_description = "Mark selected banking details as verified"

    def mark_as_primary(self, request, queryset):
        # First, unmark all others as primary
        BankingDetail.objects.update(is_primary=False)
        # Then mark selected ones as primary
        updated = queryset.update(is_primary=True)
        self.message_user(request, f"{updated} banking details marked as primary.")

    mark_as_primary.short_description = "Mark as primary banking account"

    def enable_auto_transfer(self, request, queryset):
        updated = queryset.update(is_enabled_for_auto_transfer=True)
        self.message_user(request, f"{updated} banking details enabled for auto transfer.")

    enable_auto_transfer.short_description = "Enable auto transfer"


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Choice Information', {
            'fields': ('category', 'internal_value', 'display_value'),
            'description': 'Define the choice category and its internal/display values.'
        }),
    )

    # Customize list view
    list_display = ('category', 'internal_value', 'display_value')
    list_filter = ('category',)
    search_fields = ('internal_value', 'display_value')
    ordering = ('category', 'internal_value')
