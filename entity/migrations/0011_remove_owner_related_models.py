from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0005_update_shipment_partner_refs'),
        ('entity', '0010_remove_driver_aadhaar_remove_driver_aadhaar_document_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='driver',
            old_name='owners',
            new_name='owner',
        ),
        migrations.AlterField(
            model_name='driver',
            name='owner',
            field=models.ForeignKey(
                help_text='Owner organization this driver works for (REQUIRED - industry standard)',
                limit_choices_to={'organization_type': 'OWNER'},
                on_delete=django.db.models.deletion.PROTECT,
                related_name='drivers',
                to='entity.organization',
            ),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                help_text='Owner organization responsible for this vehicle',
                limit_choices_to={'organization_type': 'OWNER'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='vehicles',
                to='entity.organization',
            ),
        ),
        migrations.DeleteModel(
            name='Broker',
        ),
        migrations.DeleteModel(
            name='Owner',
        ),
        migrations.DeleteModel(
            name='Transporter',
        ),
    ]
