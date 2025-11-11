"""
Utility module for generating PDF performance reports for supervisors and maintainers.
Provides insights into activities, ratings, and metrics related to issues and tasks.
"""

from io import BytesIO
from datetime import datetime, timedelta
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from core.models import User
from issue_management.models import Issue, WorkTask, SiteVisit


class PerformanceReportGenerator:
    """Generate PDF performance reports for supervisors and maintainers"""
    
    def __init__(self, organization, start_date=None, end_date=None, user_ids=None, include_supervisors=True, include_maintainers=True):
        """
        Initialize the report generator
        
        Args:
            organization: Organization instance to filter data
            start_date: Start date for the report period (defaults to 30 days ago)
            end_date: End date for the report period (defaults to today)
            user_ids: List of specific user IDs to include (optional)
            include_supervisors: Whether to include supervisors in the report (default: True)
            include_maintainers: Whether to include maintainers in the report (default: True)
        """
        self.organization = organization
        self.end_date = end_date or timezone.now()
        self.start_date = start_date or (self.end_date - timedelta(days=30))
        self.user_ids = user_ids
        self.include_supervisors = include_supervisors
        self.include_maintainers = include_maintainers
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles for the report"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Subheading style
        self.styles.add(ParagraphStyle(
            name='CustomSubheading',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#555555'),
            spaceAfter=8,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
        ))
    
    def get_supervisor_metrics(self, supervisor):
        """Calculate metrics for a supervisor"""
        # Issues assigned to the supervisor
        assigned_issues = Issue.objects.filter(
            assigned_to=supervisor,
            assigned_at__range=(self.start_date, self.end_date)
        )
        
        # Issues resolved in the period
        resolved_issues = assigned_issues.filter(
            status='resolved',
            updated_at__range=(self.start_date, self.end_date)
        )
        
        # Work tasks created by supervisor
        work_tasks_created = WorkTask.objects.filter(
            issue__assigned_to=supervisor,
            created_at__range=(self.start_date, self.end_date)
        )
        
        # Site visits created by supervisor
        site_visits = SiteVisit.objects.filter(
            created_by=supervisor,
            created_at__range=(self.start_date, self.end_date)
        )
        
        # Calculate average resolution time for resolved issues
        resolved_with_assignment = resolved_issues.filter(assigned_at__isnull=False)
        avg_resolution_time = None
        if resolved_with_assignment.exists():
            total_time = timedelta()
            count = 0
            for issue in resolved_with_assignment:
                if issue.assigned_at and issue.updated_at:
                    total_time += (issue.updated_at - issue.assigned_at)
                    count += 1
            if count > 0:
                avg_seconds = total_time.total_seconds() / count
                avg_resolution_time = avg_seconds / 3600  # Convert to hours
        
        # Priority breakdown
        priority_breakdown = assigned_issues.values('priority').annotate(count=Count('id'))
        
        # Status breakdown
        status_breakdown = assigned_issues.values('status').annotate(count=Count('id'))
        
        # Calculate performance rating (0-100)
        rating = self.calculate_supervisor_rating(
            total_issues=assigned_issues.count(),
            resolved_issues=resolved_issues.count(),
            avg_resolution_time=avg_resolution_time,
            tasks_created=work_tasks_created.count(),
            site_visits=site_visits.count()
        )
        
        return {
            'user': supervisor,
            'total_assigned': assigned_issues.count(),
            'resolved': resolved_issues.count(),
            'in_progress': assigned_issues.filter(status='in_progress').count(),
            'pending': assigned_issues.filter(status='assigned').count(),
            'tasks_created': work_tasks_created.count(),
            'site_visits_created': site_visits.count(),
            'avg_resolution_hours': round(avg_resolution_time, 2) if avg_resolution_time else None,
            'priority_breakdown': list(priority_breakdown),
            'status_breakdown': list(status_breakdown),
            'rating': rating
        }
    
    def get_maintainer_metrics(self, maintainer):
        """Calculate metrics for a maintainer"""
        # Work tasks assigned to the maintainer
        assigned_tasks = WorkTask.objects.filter(
            assigned_to=maintainer,
            created_at__range=(self.start_date, self.end_date)
        )
        
        # Completed tasks
        completed_tasks = assigned_tasks.filter(completed=True)
        
        # Site visits assigned to the maintainer
        assigned_visits = SiteVisit.objects.filter(
            assigned_to=maintainer,
            created_at__range=(self.start_date, self.end_date)
        )
        
        # Completed site visits
        completed_visits = assigned_visits.filter(status='completed')
        
        # Calculate average task completion time
        avg_completion_time = None
        completed_with_dates = completed_tasks.filter(
            created_at__isnull=False,
            updated_at__isnull=False
        )
        if completed_with_dates.exists():
            total_time = timedelta()
            count = 0
            for task in completed_with_dates:
                total_time += (task.updated_at - task.created_at)
                count += 1
            if count > 0:
                avg_seconds = total_time.total_seconds() / count
                avg_completion_time = avg_seconds / 3600  # Convert to hours
        
        # Issues related to completed tasks
        issues_contributed = Issue.objects.filter(
            work_tasks__in=completed_tasks
        ).distinct().count()
        
        # Priority breakdown of assigned tasks
        priority_breakdown = assigned_tasks.values('issue__priority').annotate(count=Count('id'))
        
        # Calculate performance rating (0-100)
        rating = self.calculate_maintainer_rating(
            total_tasks=assigned_tasks.count(),
            completed_tasks=completed_tasks.count(),
            completed_visits=completed_visits.count(),
            avg_completion_time=avg_completion_time,
            issues_contributed=issues_contributed
        )
        
        return {
            'user': maintainer,
            'total_tasks': assigned_tasks.count(),
            'completed_tasks': completed_tasks.count(),
            'pending_tasks': assigned_tasks.filter(completed=False).count(),
            'site_visits_assigned': assigned_visits.count(),
            'site_visits_completed': completed_visits.count(),
            'site_visits_pending': assigned_visits.exclude(status__in=['completed', 'cancelled']).count(),
            'avg_completion_hours': round(avg_completion_time, 2) if avg_completion_time else None,
            'issues_contributed': issues_contributed,
            'priority_breakdown': list(priority_breakdown),
            'rating': rating
        }
    
    def calculate_supervisor_rating(self, total_issues, resolved_issues, avg_resolution_time, 
                                   tasks_created, site_visits):
        """
        Calculate performance rating for supervisor (0-100)
        
        Criteria:
        - Resolution rate: 40% (resolved / total)
        - Speed: 30% (faster resolution time = higher score)
        - Task creation: 20% (shows proactive management)
        - Site visit coordination: 10%
        """
        if total_issues == 0:
            return 0
        
        # Resolution rate score (40 points max)
        resolution_rate = (resolved_issues / total_issues) * 100
        resolution_score = (resolution_rate / 100) * 40
        
        # Speed score (30 points max) - lower time is better
        # Assume 48 hours as benchmark (excellent), 168 hours (1 week) as poor
        speed_score = 0
        if avg_resolution_time is not None:
            if avg_resolution_time <= 48:
                speed_score = 30
            elif avg_resolution_time <= 168:
                # Linear scale between 48-168 hours
                speed_score = 30 - ((avg_resolution_time - 48) / 120) * 30
            else:
                speed_score = 0
        else:
            speed_score = 15  # Neutral score if no data
        
        # Task creation score (20 points max)
        # Benchmark: 2 tasks per issue is excellent
        tasks_per_issue = tasks_created / total_issues if total_issues > 0 else 0
        task_score = min(tasks_per_issue / 2, 1) * 20
        
        # Site visit score (10 points max)
        # Benchmark: 0.5 visits per issue is good
        visits_per_issue = site_visits / total_issues if total_issues > 0 else 0
        visit_score = min(visits_per_issue / 0.5, 1) * 10
        
        total_rating = resolution_score + speed_score + task_score + visit_score
        return round(min(total_rating, 100), 1)
    
    def calculate_maintainer_rating(self, total_tasks, completed_tasks, completed_visits,
                                   avg_completion_time, issues_contributed):
        """
        Calculate performance rating for maintainer (0-100)
        
        Criteria:
        - Completion rate: 50% (completed / total)
        - Speed: 30% (faster completion time = higher score)
        - Site visits: 15%
        - Issue contribution: 5% (unique issues worked on)
        """
        if total_tasks == 0:
            return 0
        
        # Completion rate score (50 points max)
        completion_rate = (completed_tasks / total_tasks) * 100
        completion_score = (completion_rate / 100) * 50
        
        # Speed score (30 points max)
        # Assume 24 hours as excellent, 72 hours as poor
        speed_score = 0
        if avg_completion_time is not None:
            if avg_completion_time <= 24:
                speed_score = 30
            elif avg_completion_time <= 72:
                speed_score = 30 - ((avg_completion_time - 24) / 48) * 30
            else:
                speed_score = 0
        else:
            speed_score = 15  # Neutral score if no data
        
        # Site visit score (15 points max)
        # Benchmark: 1 visit per 2 tasks is good
        visit_score = 0
        if completed_visits > 0:
            visits_per_task = completed_visits / total_tasks if total_tasks > 0 else 0
            visit_score = min(visits_per_task / 0.5, 1) * 15
        
        # Issue contribution score (5 points max)
        # Benchmark: contributing to 5+ unique issues is excellent
        contribution_score = min(issues_contributed / 5, 1) * 5
        
        total_rating = completion_score + speed_score + visit_score + contribution_score
        return round(min(total_rating, 100), 1)
    
    def get_rating_label(self, rating):
        """Get text label for rating"""
        if rating >= 90:
            return "Excellent"
        elif rating >= 75:
            return "Good"
        elif rating >= 60:
            return "Satisfactory"
        elif rating >= 40:
            return "Needs Improvement"
        else:
            return "Poor"
    
    def get_rating_color(self, rating):
        """Get color for rating"""
        if rating >= 90:
            return colors.HexColor('#10b981')  # Green
        elif rating >= 75:
            return colors.HexColor('#3b82f6')  # Blue
        elif rating >= 60:
            return colors.HexColor('#f59e0b')  # Amber
        elif rating >= 40:
            return colors.HexColor('#f97316')  # Orange
        else:
            return colors.HexColor('#ef4444')  # Red
    
    def generate_report(self):
        """Generate the complete PDF report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        
        # Title
        title = Paragraph(
            f"<b>Performance Report</b><br/>{self.organization.name}",
            self.styles['CustomTitle']
        )
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Report period
        period_text = f"Report Period: {self.start_date.strftime('%B %d, %Y')} - {self.end_date.strftime('%B %d, %Y')}"
        period = Paragraph(period_text, self.styles['CustomBody'])
        story.append(period)
        story.append(Spacer(1, 0.3*inch))
        
        # Get users to include based on role filters
        supervisors = User.objects.none()  # Empty queryset by default
        maintainers = User.objects.none()  # Empty queryset by default
        
        if self.include_supervisors:
            supervisors = User.objects.filter(
                organization=self.organization,
                user_type='supervisor',
                is_active=True
            )
        
        if self.include_maintainers:
            maintainers = User.objects.filter(
                organization=self.organization,
                user_type='maintainer',
                is_active=True
            )
        
        # Filter by specific user IDs if provided
        if self.user_ids:
            supervisors = supervisors.filter(id__in=self.user_ids)
            maintainers = maintainers.filter(id__in=self.user_ids)
        
        # Collect all data first
        supervisor_data = []
        maintainer_data = []
        
        # Supervisor section
        if supervisors.exists():
            story.append(Paragraph("<b>Supervisor Performance</b>", self.styles['CustomHeading']))
            story.append(Spacer(1, 0.1*inch))
            
            # Collect supervisor data
            for supervisor in supervisors:
                metrics = self.get_supervisor_metrics(supervisor)
                supervisor_data.append(metrics)
            
            # Sort by rating (highest first)
            supervisor_data.sort(key=lambda x: x['rating'], reverse=True)
            
            # Create detailed section for each supervisor
            for i, data in enumerate(supervisor_data):
                # Wrap each supervisor section in KeepTogether to prevent page breaks
                section_elements = self.create_supervisor_section(data)
                story.append(KeepTogether(section_elements))
                # Add spacer between entries, but not after the last one
                if i < len(supervisor_data) - 1:
                    story.append(Spacer(1, 0.3*inch))
        
        # Maintainer section
        if maintainers.exists():
            # Add spacing between sections if we had supervisors
            if supervisor_data:
                story.append(Spacer(1, 0.4*inch))
            
            story.append(Paragraph("<b>Maintainer Performance</b>", self.styles['CustomHeading']))
            story.append(Spacer(1, 0.1*inch))
            
            # Collect maintainer data
            for maintainer in maintainers:
                metrics = self.get_maintainer_metrics(maintainer)
                maintainer_data.append(metrics)
            
            # Sort by rating (highest first)
            maintainer_data.sort(key=lambda x: x['rating'], reverse=True)
            
            # Create detailed section for each maintainer
            for i, data in enumerate(maintainer_data):
                # Wrap each maintainer section in KeepTogether to prevent page breaks
                section_elements = self.create_maintainer_section(data)
                story.append(KeepTogether(section_elements))
                # Add spacer between entries, but not after the last one
                if i < len(maintainer_data) - 1:
                    story.append(Spacer(1, 0.3*inch))
        
        # Summary section - only add if we have data
        if supervisor_data or maintainer_data:
            story.append(Spacer(1, 0.5*inch))
            story.extend(self.create_summary_section(supervisor_data, maintainer_data))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def create_supervisor_section(self, data):
        """Create report section for a single supervisor"""
        elements = []
        
        # Name and rating
        user = data['user']
        name = user.get_full_name() or user.email
        rating = data['rating']
        rating_label = self.get_rating_label(rating)
        rating_color = self.get_rating_color(rating)
        
        # Name heading
        elements.append(Paragraph(f"<b>{name}</b>", self.styles['CustomSubheading']))
        
        # Rating with color
        rating_text = f'<font color="{rating_color.hexval()}"><b>Rating: {rating}/100 ({rating_label})</b></font>'
        elements.append(Paragraph(rating_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Metrics table
        table_data = [
            ['Metric', 'Value'],
            ['Issues Assigned', str(data['total_assigned'])],
            ['Issues Resolved', str(data['resolved'])],
            ['Issues In Progress', str(data['in_progress'])],
            ['Issues Pending', str(data['pending'])],
            ['Work Tasks Created', str(data['tasks_created'])],
            ['Site Visits Coordinated', str(data['site_visits_created'])],
            ['Avg. Resolution Time', f"{data['avg_resolution_hours']} hours" if data['avg_resolution_hours'] else 'N/A'],
        ]
        
        table = Table(table_data, colWidths=[3.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        
        return elements
    
    def create_maintainer_section(self, data):
        """Create report section for a single maintainer"""
        elements = []
        
        # Name and rating
        user = data['user']
        name = user.get_full_name() or user.email
        rating = data['rating']
        rating_label = self.get_rating_label(rating)
        rating_color = self.get_rating_color(rating)
        
        # Name heading
        elements.append(Paragraph(f"<b>{name}</b>", self.styles['CustomSubheading']))
        
        # Rating with color
        rating_text = f'<font color="{rating_color.hexval()}"><b>Rating: {rating}/100 ({rating_label})</b></font>'
        elements.append(Paragraph(rating_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Metrics table
        table_data = [
            ['Metric', 'Value'],
            ['Work Tasks Assigned', str(data['total_tasks'])],
            ['Tasks Completed', str(data['completed_tasks'])],
            ['Tasks Pending', str(data['pending_tasks'])],
            ['Site Visits Assigned', str(data['site_visits_assigned'])],
            ['Site Visits Completed', str(data['site_visits_completed'])],
            ['Site Visits Pending', str(data['site_visits_pending'])],
            ['Avg. Task Completion Time', f"{data['avg_completion_hours']} hours" if data['avg_completion_hours'] else 'N/A'],
            ['Issues Contributed To', str(data['issues_contributed'])],
        ]
        
        table = Table(table_data, colWidths=[3.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        
        return elements
    
    def create_summary_section(self, supervisor_data, maintainer_data):
        """Create summary statistics section"""
        elements = []
        
        # Summary Statistics - keep together
        summary_elements = []
        summary_elements.append(Paragraph("<b>Summary Statistics</b>", self.styles['CustomHeading']))
        summary_elements.append(Spacer(1, 0.1*inch))
        
        # Calculate overall statistics
        summary_data = [
            ['Category', 'Count', 'Avg. Rating'],
        ]
        
        if supervisor_data:
            supervisor_count = len(supervisor_data)
            avg_supervisor_rating = sum(d['rating'] for d in supervisor_data) / supervisor_count
            summary_data.append(['Supervisors', str(supervisor_count), f"{round(avg_supervisor_rating, 1)}/100"])
        
        if maintainer_data:
            maintainer_count = len(maintainer_data)
            avg_maintainer_rating = sum(d['rating'] for d in maintainer_data) / maintainer_count
            summary_data.append(['Maintainers', str(maintainer_count), f"{round(avg_maintainer_rating, 1)}/100"])
        
        table = Table(summary_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        summary_elements.append(table)
        elements.append(KeepTogether(summary_elements))
        elements.append(Spacer(1, 0.3*inch))
        
        # Top performers - keep together
        if supervisor_data or maintainer_data:
            top_elements = []
            top_elements.append(Paragraph("<b>Top Performers</b>", self.styles['CustomSubheading']))
            top_elements.append(Spacer(1, 0.1*inch))
            
            top_data = [['Name', 'Role', 'Rating']]
            
            # Get top 3 from each category
            top_supervisors = sorted(supervisor_data, key=lambda x: x['rating'], reverse=True)[:3]
            top_maintainers = sorted(maintainer_data, key=lambda x: x['rating'], reverse=True)[:3]
            
            for data in top_supervisors:
                name = data['user'].get_full_name() or data['user'].email
                top_data.append([name, 'Supervisor', f"{data['rating']}/100"])
            
            for data in top_maintainers:
                name = data['user'].get_full_name() or data['user'].email
                top_data.append([name, 'Maintainer', f"{data['rating']}/100"])
            
            if len(top_data) > 1:  # Only create table if there's data
                top_table = Table(top_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
                top_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('TOPPADDING', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                top_elements.append(top_table)
                elements.append(KeepTogether(top_elements))
        
        return elements
