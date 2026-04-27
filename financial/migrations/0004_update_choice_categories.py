import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0003_officeexpense_and_more'),
        ('configuration', '0006_alter_choice_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='officeexpense',
            name='category',
            field=models.ForeignKey(blank=True, limit_choices_to={'category': 'FINANCE_EXPENSE_CATEGORY'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='other_expense_set', to='configuration.choice'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.ForeignKey(blank=True, limit_choices_to={'category': 'FINANCE_PAYMENT_MODE'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_mode_set', to='configuration.choice'),
        ),
    ]
