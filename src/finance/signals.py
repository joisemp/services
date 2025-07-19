from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from .models import FinancialTransaction, TransactionCategory
from .utils import create_transaction_from_object


@receiver(post_save, sender='issue_management.Issue')
def create_issue_transaction(sender, instance, created, **kwargs):
    """Create a transaction when an issue is created (if it has associated costs)"""
    if created and hasattr(instance, 'estimated_cost') and instance.estimated_cost:
        # Get or create a category for issues
        category, _ = TransactionCategory.objects.get_or_create(
            name='Issue Management',
            org=instance.org,
            defaults={'description': 'Costs related to issue management and resolution'}
        )
        
        # Create expense transaction
        create_transaction_from_object(
            obj=instance,
            amount=instance.estimated_cost,
            transaction_type='expense',
            title=f'Issue Resolution Cost - {instance.title}',
            description=f'Estimated cost for resolving issue: {instance.description[:100]}...',
            category=category,
            user=instance.created_by
        )


@receiver(post_save, sender='service_management.WorkCategory')
def create_service_transaction(sender, instance, created, **kwargs):
    """Create a transaction when a service is provided (if it has associated costs)"""
    if created and hasattr(instance, 'service_cost') and instance.service_cost:
        # Get or create a category for services
        category, _ = TransactionCategory.objects.get_or_create(
            name='Service Management',
            org=instance.org,
            defaults={'description': 'Costs related to service provision and management'}
        )
        
        # Create expense transaction
        create_transaction_from_object(
            obj=instance,
            amount=instance.service_cost,
            transaction_type='expense',
            title=f'Service Cost - {instance.name}',
            description=f'Cost for service: {instance.description[:100]}...',
            category=category,
            user=getattr(instance, 'created_by', None)
        )


@receiver(post_save, sender='marketplace.Purchase')
def create_purchase_transaction(sender, instance, created, **kwargs):
    """Create transactions for marketplace purchases"""
    if created and hasattr(instance, 'total_cost') and instance.total_cost:
        # Get or create a category for marketplace
        category, _ = TransactionCategory.objects.get_or_create(
            name='Marketplace',
            org=instance.org,
            defaults={'description': 'Expenses from marketplace purchases'}
        )
        
        # Create expense transaction for the purchase
        create_transaction_from_object(
            obj=instance,
            amount=instance.total_cost,
            transaction_type='expense',
            title=f'Marketplace Purchase - {instance.supplier}',
            description=f'Purchase from {instance.supplier}',
            category=category,
            user=instance.created_by
        )


@receiver(post_save, sender='transportation.Vehicle')
def create_vehicle_transaction(sender, instance, created, **kwargs):
    """Create a transaction when a vehicle is registered (if it has associated costs)"""
    if created and hasattr(instance, 'purchase_price') and instance.purchase_price:
        # Get or create a category for transportation
        category, _ = TransactionCategory.objects.get_or_create(
            name='Transportation',
            org=instance.organisation,
            defaults={'description': 'Costs related to transportation and vehicle management'}
        )
        
        # Create expense transaction
        create_transaction_from_object(
            obj=instance,
            amount=instance.purchase_price,
            transaction_type='expense',
            title=f'Vehicle Purchase - {instance.make} {instance.model}',
            description=f'Purchase of vehicle: {instance.license_plate}',
            category=category,
            user=getattr(instance, 'created_by', None)
        )


@receiver(post_save, sender='transportation.MaintenanceRecord')
def create_maintenance_transaction(sender, instance, created, **kwargs):
    """Create a transaction when a maintenance record is created"""
    if created and hasattr(instance, 'cost') and instance.cost:
        # Get or create a category for maintenance
        category, _ = TransactionCategory.objects.get_or_create(
            name='Vehicle Maintenance',
            org=instance.vehicle.organisation,
            defaults={'description': 'Costs related to vehicle maintenance and repairs'}
        )
        
        # Create expense transaction
        create_transaction_from_object(
            obj=instance,
            amount=instance.cost,
            transaction_type='expense',
            title=f'Vehicle Maintenance - {instance.vehicle.license_plate}',
            description=f'Maintenance: {instance.description[:100]}...',
            category=category,
            user=instance.performed_by
        )


@receiver(post_save, sender='core.UserProfile')
def create_user_registration_transaction(sender, instance, created, **kwargs):
    """Create a transaction when a new user registers (if there are registration fees)"""
    if created and hasattr(instance, 'registration_fee') and instance.registration_fee:
        # Get or create a category for registration
        category, _ = TransactionCategory.objects.get_or_create(
            name='User Registration',
            org=instance.org,
            defaults={'description': 'Fees and costs related to user registration'}
        )
        
        # Create income transaction for registration fee
        create_transaction_from_object(
            obj=instance,
            amount=instance.registration_fee,
            transaction_type='income',
            title=f'Registration Fee - {instance.user.email}',
            description=f'Registration fee for new user',
            category=category,
            user=instance.user
        )


# Signal to track when transactions are deleted
@receiver(post_delete, sender=FinancialTransaction)
def log_transaction_deletion(sender, instance, **kwargs):
    """Log when a transaction is deleted for audit purposes"""
    from django.contrib.admin.models import LogEntry, DELETION
    from django.contrib.contenttypes.models import ContentType
    
    # Create log entry
    LogEntry.objects.create(
        user_id=1,  # System user or the user who deleted it
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.id,
        object_repr=str(instance),
        action_flag=DELETION,
        change_message=f'Transaction {instance.transaction_id} deleted'
    )


# Signal to update budget usage when transactions are created/updated
@receiver(post_save, sender=FinancialTransaction)
def update_budget_usage(sender, instance, created, **kwargs):
    """Update budget usage when transactions are created or updated"""
    if instance.transaction_type == 'expense' and instance.status == 'completed':
        from .models import Budget
        
        # Find relevant budgets
        budgets = Budget.objects.filter(
            org=instance.org,
            is_active=True,
            start_date__lte=instance.transaction_date.date(),
            end_date__gte=instance.transaction_date.date()
        )
        
        # If transaction has a category, also check category-specific budgets
        if instance.category:
            budgets = budgets.filter(
                Q(category=instance.category) | Q(category__isnull=True)
            )
        else:
            budgets = budgets.filter(category__isnull=True)
        
        # Check if any budgets are over limit and send notifications
        for budget in budgets:
            if budget.is_over_budget():
                # Here you could send notifications, emails, etc.
                # For now, we'll just pass
                pass


# Signal to automatically categorize transactions
@receiver(post_save, sender=FinancialTransaction)
def auto_categorize_transaction(sender, instance, created, **kwargs):
    """Automatically categorize transactions based on keywords"""
    if created and not instance.category:
        # Define keyword mappings
        keyword_mappings = {
            'transportation': ['transport', 'fuel', 'gas', 'taxi', 'uber', 'bus', 'train', 'vehicle', 'maintenance'],
            'utilities': ['electricity', 'water', 'internet', 'phone', 'utility'],
            'supplies': ['supplies', 'equipment', 'materials', 'tools'],
            'maintenance': ['maintenance', 'repair', 'fix', 'service'],
            'food': ['food', 'meal', 'restaurant', 'catering', 'lunch', 'dinner'],
            'office': ['office', 'stationery', 'paper', 'printing', 'furniture'],
            'marketplace': ['purchase', 'buy', 'shopping', 'vendor', 'supplier'],
            'issue management': ['issue', 'problem', 'resolution', 'fix', 'bug'],
            'service management': ['service', 'work', 'category', 'support'],
        }
        
        # Check title and description for keywords
        text_to_check = f"{instance.title} {instance.description}".lower()
        
        for category_name, keywords in keyword_mappings.items():
            if any(keyword in text_to_check for keyword in keywords):
                # Try to find or create the category
                try:
                    category = TransactionCategory.objects.get(
                        name__icontains=category_name,
                        org=instance.org,
                        is_active=True
                    )
                    instance.category = category
                    instance.save(update_fields=['category'])
                    break
                except TransactionCategory.DoesNotExist:
                    # Create a new category
                    category = TransactionCategory.objects.create(
                        name=category_name.title(),
                        org=instance.org,
                        description=f'Auto-created category for {category_name}-related transactions'
                    )
                    instance.category = category
                    instance.save(update_fields=['category'])
                    break
