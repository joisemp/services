# Data-preserving rename: Issue* → Ticket*, issue fields → ticket fields.
# For existing DBs that still have issue_management_* tables / migration rows,
# run `python manage.py relabel_issue_to_ticket_app` before this migration.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ticket_management', '0027_issue_workshop'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Models ---
        migrations.RenameModel(old_name='Issue', new_name='Ticket'),
        migrations.RenameModel(old_name='IssueImage', new_name='TicketImage'),
        migrations.RenameModel(old_name='IssueComment', new_name='TicketComment'),
        migrations.RenameModel(old_name='IssueResolutionImage', new_name='TicketResolutionImage'),
        migrations.RenameModel(old_name='IssueReviewComment', new_name='TicketReviewComment'),
        migrations.RenameModel(old_name='IssueReviewCommentImage', new_name='TicketReviewCommentImage'),
        migrations.RenameModel(old_name='IssueActivity', new_name='TicketActivity'),

        # --- Ticket fields ---
        migrations.RenameField(model_name='ticket', old_name='issue_id', new_name='ticket_id'),

        # --- FK field issue → ticket on related models ---
        migrations.RenameField(model_name='ticketimage', old_name='issue', new_name='ticket'),
        migrations.RenameField(model_name='ticketcomment', old_name='issue', new_name='ticket'),
        migrations.RenameField(model_name='ticketresolutionimage', old_name='issue', new_name='ticket'),
        migrations.RenameField(model_name='ticketreviewcomment', old_name='issue', new_name='ticket'),
        migrations.RenameField(model_name='ticketactivity', old_name='issue', new_name='ticket'),
        migrations.RenameField(model_name='worktask', old_name='issue', new_name='ticket'),
        migrations.RenameField(model_name='sitevisit', old_name='issue', new_name='ticket'),
        migrations.RenameField(model_name='purchaserequest', old_name='issue', new_name='ticket'),

        # --- Snapshot field on shopping list items ---
        migrations.RenameField(
            model_name='shoppinglistitem',
            old_name='issue_title',
            new_name='ticket_title',
        ),

        # --- related_name / help_text / verbose names (state + DB where applicable) ---
        migrations.AlterField(
            model_name='ticket',
            name='assigned_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Who assigned this ticket',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tickets_assigned_by_me',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='assigned_to',
            field=models.ForeignKey(
                blank=True,
                help_text='Supervisor assigned to handle this ticket',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_tickets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='org',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tickets',
                to='core.organization',
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='reporter',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='reported_tickets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='reviewed_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Who reviewed this ticket (if review required)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_tickets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='reviewers',
            field=models.ManyToManyField(
                blank=True,
                help_text='Users assigned to review this ticket when requires_review is checked',
                related_name='tickets_to_review',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='space',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tickets',
                to='core.space',
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='ticket_id',
            field=models.CharField(
                help_text='Unique identifier for the ticket',
                max_length=20,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='vehicle',
            field=models.ForeignKey(
                blank=True,
                help_text='Vehicle associated with this ticket (optional)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tickets',
                to='fleet_management.vehicle',
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='workshop',
            field=models.ForeignKey(
                blank=True,
                help_text='Workshop where this ticket should be reported',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tickets',
                to='fleet_management.workshop',
            ),
        ),
        migrations.AlterField(
            model_name='ticketcomment',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ticket_comments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='ticketreviewcomment',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ticket_review_comments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='ticketactivity',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ticket_activities',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='shoppinglistitem',
            name='ticket_title',
            field=models.CharField(
                help_text='Ticket title at time of list generation',
                max_length=200,
            ),
        ),
        migrations.AlterModelOptions(
            name='ticketactivity',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Ticket Activity',
                'verbose_name_plural': 'Ticket Activities',
            },
        ),
        migrations.AlterModelOptions(
            name='ticketreviewcomment',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Ticket Review Comment',
                'verbose_name_plural': 'Ticket Review Comments',
            },
        ),
    ]
