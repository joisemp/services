from django.apps import AppConfig


class IssueManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'issue_management'
    
    def ready(self):
        # Import signals to register them
        import issue_management.signals
