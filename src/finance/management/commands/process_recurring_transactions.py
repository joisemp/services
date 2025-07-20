from django.core.management.base import BaseCommand
from django.utils import timezone
from finance.models import RecurringTransaction


class Command(BaseCommand):
    help = 'Process due recurring transactions and create new transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually creating transactions',
        )
        parser.add_argument(
            '--org-id',
            type=int,
            help='Process recurring transactions for a specific organization only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        org_id = options['org_id']
        
        # Get due recurring transactions
        due_recurring = RecurringTransaction.objects.filter(
            is_active=True,
            auto_create=True,
            next_due_date__lte=timezone.now().date()
        )
        
        if org_id:
            due_recurring = due_recurring.filter(org_id=org_id)
        
        if not due_recurring.exists():
            self.stdout.write(
                self.style.SUCCESS('No due recurring transactions found.')
            )
            return
        
        processed_count = 0
        error_count = 0
        
        for recurring in due_recurring:
            try:
                if dry_run:
                    self.stdout.write(
                        f'Would process: {recurring.title} - {recurring.amount} '
                        f'({recurring.org.name}) - Due: {recurring.next_due_date}'
                    )
                else:
                    transaction = recurring.create_transaction()
                    self.stdout.write(
                        f'Created transaction: {transaction.title} - {transaction.amount} '
                        f'({transaction.org.name}) - ID: {transaction.transaction_id}'
                    )
                
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Error processing {recurring.title}: {str(e)}'
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Dry run complete. Would have processed {processed_count} recurring transactions.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed {processed_count} recurring transactions.'
                )
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'{error_count} errors encountered during processing.'
                )
            )
