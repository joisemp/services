"""
Test script to verify performance report generation
Run this in Django shell: python manage.py shell < test_report.py
"""

from django.utils import timezone
from datetime import timedelta
from core.models import User, Organization
from issue_management.utils.performance_report import PerformanceReportGenerator

print("Testing Performance Report Generator...")
print("-" * 50)

# Get or create test organization
org, _ = Organization.objects.get_or_create(
    name="Test Organization",
    defaults={
        'description': 'Test organization for report generation'
    }
)

print(f"Using organization: {org.name}")

# Get supervisors and maintainers
supervisors = User.objects.filter(organization=org, user_type='supervisor', is_active=True)
maintainers = User.objects.filter(organization=org, user_type='maintainer', is_active=True)

print(f"Supervisors found: {supervisors.count()}")
print(f"Maintainers found: {maintainers.count()}")

if supervisors.count() == 0 and maintainers.count() == 0:
    print("\nNo supervisors or maintainers found. Create some users first!")
    print("You can do this through the Django admin or create them programmatically.")
else:
    # Test report generation
    print("\nGenerating test report...")
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"Report period: {start_date.date()} to {end_date.date()}")
    
    try:
        generator = PerformanceReportGenerator(
            organization=org,
            start_date=start_date,
            end_date=end_date,
            user_ids=None  # Include all users
        )
        
        # Test metric calculation for each supervisor
        print("\n" + "=" * 50)
        print("SUPERVISOR METRICS:")
        print("=" * 50)
        for supervisor in supervisors[:3]:  # Show first 3
            metrics = generator.get_supervisor_metrics(supervisor)
            print(f"\n{supervisor.get_full_name() or supervisor.email}:")
            print(f"  Rating: {metrics['rating']}/100 ({generator.get_rating_label(metrics['rating'])})")
            print(f"  Issues Assigned: {metrics['total_assigned']}")
            print(f"  Issues Resolved: {metrics['resolved']}")
            print(f"  Avg Resolution Time: {metrics['avg_resolution_hours']} hours" if metrics['avg_resolution_hours'] else "  Avg Resolution Time: N/A")
        
        # Test metric calculation for each maintainer
        print("\n" + "=" * 50)
        print("MAINTAINER METRICS:")
        print("=" * 50)
        for maintainer in maintainers[:3]:  # Show first 3
            metrics = generator.get_maintainer_metrics(maintainer)
            print(f"\n{maintainer.get_full_name() or maintainer.email}:")
            print(f"  Rating: {metrics['rating']}/100 ({generator.get_rating_label(metrics['rating'])})")
            print(f"  Tasks Assigned: {metrics['total_tasks']}")
            print(f"  Tasks Completed: {metrics['completed_tasks']}")
            print(f"  Avg Completion Time: {metrics['avg_completion_hours']} hours" if metrics['avg_completion_hours'] else "  Avg Completion Time: N/A")
        
        # Generate actual PDF
        print("\n" + "=" * 50)
        print("GENERATING PDF...")
        print("=" * 50)
        pdf_buffer = generator.generate_report()
        
        print(f"✓ PDF generated successfully!")
        print(f"  Size: {len(pdf_buffer.getvalue())} bytes")
        
        # Optionally save to file for testing
        # with open('test_report.pdf', 'wb') as f:
        #     f.write(pdf_buffer.getvalue())
        # print("  Saved as: test_report.pdf")
        
    except Exception as e:
        print(f"\n✗ Error generating report: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 50)
print("Test completed!")
print("=" * 50)
