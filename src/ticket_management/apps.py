from django.apps import AppConfig
from django.db.models.signals import pre_migrate


def _auto_relabel_issue_to_ticket(sender, app_config, **kwargs):
    """Rewrite issue_management history/tables before ticket_management migrations."""
    if getattr(app_config, 'name', None) != 'ticket_management':
        return
    from ticket_management.relabel_app import relabel_issue_to_ticket_app

    relabel_issue_to_ticket_app()


class TicketManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ticket_management'

    def ready(self):
        # Import signals to register them
        import ticket_management.signals  # noqa: F401

        pre_migrate.connect(
            _auto_relabel_issue_to_ticket,
            sender=self,
            dispatch_uid='ticket_management.auto_relabel_issue_to_ticket',
        )
