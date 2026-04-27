import django.db.models.deletion
from django.db import migrations, models


TRANSACTION_CHOICES = {
    'Install': 'Install',
    'Replace': 'Replace',
    'Rotate': 'Rotate',
    'Remove': 'Remove',
    'Service': 'Service',
}


def populate_transaction_type_fk(apps, schema_editor):
    Choice = apps.get_model('configuration', 'Choice')
    TyreTransaction = apps.get_model('maintenance', 'TyreTransaction')

    choice_map = {}
    for internal, display in TRANSACTION_CHOICES.items():
        choice, _ = Choice.objects.get_or_create(
            category='MAINTENANCE_TRANSACTION_TYPE',
            internal_value=internal,
            defaults={'display_value': display},
        )
        choice_map[internal] = choice

    for txn in TyreTransaction.objects.all().iterator():
        legacy_value = getattr(txn, 'transaction_type', None)
        if not legacy_value:
            continue
        choice = choice_map.get(legacy_value)
        if choice:
            txn.transaction_type_new_id = choice.id
            txn.save(update_fields=['transaction_type_new'])


def revert_transaction_type_char(apps, schema_editor):
    TyreTransaction = apps.get_model('maintenance', 'TyreTransaction')

    for txn in TyreTransaction.objects.select_related('transaction_type_new').iterator():
        choice = getattr(txn, 'transaction_type_new', None)
        txn.transaction_type = choice.internal_value if choice else None
        txn.save(update_fields=['transaction_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0008_alter_maintenancerecord_content_type'),
        ('configuration', '0006_alter_choice_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='tyretransaction',
            name='transaction_type_new',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tyre_transactions_temp',
                limit_choices_to={'category': 'MAINTENANCE_TRANSACTION_TYPE'},
                to='configuration.choice',
                help_text='Temporary field for migrating transaction type to configuration.Choice',
            ),
        ),
        migrations.RunPython(populate_transaction_type_fk, revert_transaction_type_char),
        migrations.RemoveField(
            model_name='tyretransaction',
            name='transaction_type',
        ),
        migrations.RenameField(
            model_name='tyretransaction',
            old_name='transaction_type_new',
            new_name='transaction_type',
        ),
        migrations.AlterField(
            model_name='tyretransaction',
            name='transaction_type',
            field=models.ForeignKey(blank=True, limit_choices_to={'category': 'MAINTENANCE_TRANSACTION_TYPE'}, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tyre_transactions', to='configuration.choice'),
        ),
    ]
