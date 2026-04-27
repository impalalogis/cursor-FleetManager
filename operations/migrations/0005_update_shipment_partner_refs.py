from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0004_remove_shipment_non_negative_advance_and_more'),
        ('entity', '0010_remove_driver_aadhaar_remove_driver_aadhaar_document_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shipment',
            name='broker',
            field=models.ForeignKey(
                blank=True,
                help_text='Broker organization facilitating the shipment',
                null=True,
                on_delete=models.SET_NULL,
                related_name='broker_shipments',
                to='entity.organization',
                limit_choices_to={'organization_type': 'BROKER'},
            ),
        ),
        migrations.AlterField(
            model_name='shipment',
            name='transporter',
            field=models.ForeignKey(
                blank=True,
                help_text='Transporter organization handling the shipment',
                null=True,
                on_delete=models.SET_NULL,
                related_name='transporter_shipments',
                to='entity.organization',
                limit_choices_to={'organization_type': 'TRANSPORTER'},
            ),
        ),
    ]
