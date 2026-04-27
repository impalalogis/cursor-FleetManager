import django.db.models.deletion
from django.db import migrations, models


def populate_account_type_fk(apps, schema_editor):
    Choice = apps.get_model('configuration', 'Choice')
    BankingDetail = apps.get_model('configuration', 'BankingDetail')

    account_type_map = {
        'SAVINGS': 'Savings Account',
        'CURRENT': 'Current Account',
        'BUSINESS': 'Business Account',
        'OVERDRAFT': 'Overdraft Account',
        'JOINT': 'Joint Account',
    }

    choices = {}
    for internal, display in account_type_map.items():
        choice, _ = Choice.objects.get_or_create(
            category='BANK_ACCOUNT_TYPE',
            internal_value=internal,
            defaults={'display_value': display},
        )
        choices[internal] = choice

    for detail in BankingDetail.objects.all().iterator():
        legacy_value = getattr(detail, 'account_type', None)
        if not legacy_value:
            continue
        choice = choices.get(legacy_value)
        if choice:
            detail.account_type_new_id = choice.id
            detail.save(update_fields=['account_type_new'])


def revert_account_type_char(apps, schema_editor):
    BankingDetail = apps.get_model('configuration', 'BankingDetail')

    for detail in BankingDetail.objects.select_related('account_type_new').iterator():
        choice = getattr(detail, 'account_type_new', None)
        detail.account_type = choice.internal_value if choice else None
        detail.save(update_fields=['account_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0006_alter_choice_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankingdetail',
            name='account_type_new',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='banking_account_type_set',
                limit_choices_to={'category': 'BANK_ACCOUNT_TYPE'},
                to='configuration.choice',
                help_text='Temporary field for migrating account type to configuration.Choice',
            ),
        ),
        migrations.RunPython(populate_account_type_fk, revert_account_type_char),
        migrations.RemoveField(
            model_name='bankingdetail',
            name='account_type',
        ),
        migrations.RenameField(
            model_name='bankingdetail',
            old_name='account_type_new',
            new_name='account_type',
        ),
        migrations.AlterField(
            model_name='bankingdetail',
            name='account_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='banking_account_type_set',
                limit_choices_to={'category': 'BANK_ACCOUNT_TYPE'},
                to='configuration.choice',
                help_text='Type of bank account (managed via configuration choices)',
            ),
        ),
    ]
