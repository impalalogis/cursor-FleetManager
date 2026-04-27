import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0006_alter_driveradvance_content_type_and_more'),
        ('configuration', '0006_alter_choice_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='consignment',
            name='material_type',
            field=models.ForeignKey(blank=True, default=1, help_text='Specific material type (e.g., Steel, Electronics, Food Items)', limit_choices_to={'category': 'SHIPMENT_MATERIAL_TYPE'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consignment_material_type_set', to='configuration.choice'),
        ),
        migrations.AlterField(
            model_name='consignment',
            name='weight_unit',
            field=models.ForeignKey(blank=True, default=1, help_text='Unit of weight measurement', limit_choices_to={'category': 'WEIGHT_UNIT'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consignment_weight_unit_set', to='configuration.choice'),
        ),
        migrations.AlterField(
            model_name='consignment',
            name='packaging_type',
            field=models.ForeignKey(blank=True, help_text='Type of packaging (boxes, pallets, loose, etc.)', limit_choices_to={'category': 'SHIPMENT_PACKAGING_TYPE'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consignment_packaging_set', to='configuration.choice'),
        ),
        migrations.AlterField(
            model_name='consignment',
            name='freight_mode',
            field=models.ForeignKey(blank=True, help_text='Freight calculation mode (Rate, Fixed, etc.)', limit_choices_to={'category': 'SHIPMENT_FREIGHT_MODE'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consignment_freight_mode_set', to='configuration.choice'),
        ),
        migrations.AlterField(
            model_name='shipment',
            name='transporter',
            field=models.ForeignKey(blank=True, help_text='Transporter organization handling the shipment', limit_choices_to={'organization_type__internal_value': 'TRANSPORTER'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transporter_shipments', to='entity.organization'),
        ),
        migrations.AlterField(
            model_name='shipment',
            name='broker',
            field=models.ForeignKey(blank=True, help_text='Broker organization facilitating the shipment', limit_choices_to={'organization_type__internal_value': 'BROKER'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='broker_shipments', to='entity.organization'),
        ),
        migrations.AlterField(
            model_name='shipmentexpense',
            name='expense_type',
            field=models.ForeignKey(blank=True, limit_choices_to={'category': 'FINANCE_EXPENSE_TYPE'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shipment_expense_set', to='configuration.choice'),
        ),
        migrations.AlterField(
            model_name='shipmentstatus',
            name='status',
            field=models.ForeignKey(blank=True, limit_choices_to={'category': 'GENERAL_STATUS'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shipment_status_log_set', to='configuration.choice'),
        ),
        migrations.AlterField(
            model_name='shipmentstatus',
            name='shipment_doc_type',
            field=models.ForeignKey(blank=True, limit_choices_to={'category': 'SHIPMENT_DOCUMENT_TYPE'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shipment_doc_type', to='configuration.choice'),
        ),
    ]
