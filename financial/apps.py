from django.apps import AppConfig


class FinancialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financial'
    def ready(self):
        import financial.signals