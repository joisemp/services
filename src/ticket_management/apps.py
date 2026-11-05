from django.apps import AppConfig


class TicketManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ticket_management'
    
    def ready(self):
        # Import signals to register them
        import ticket_management.signals
