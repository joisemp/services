"""
Generators for Ticket List reports (PDF and Excel).

Each generator receives a pre-filtered Ticket queryset plus a set of filter
description strings and produces a downloadable file in a BytesIO buffer.
"""

from io import BytesIO

from django.db.models import Count, Q
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


# ---------------------------------------------------------------------------
# Shared data helpers
# ---------------------------------------------------------------------------

def _build_summary(queryset):
    """
    Return a dict with summary counts over *queryset*:
      - by_status    : {status_value: count, ...}
      - assigned     : count of issues with assigned_to set
      - unassigned   : count of issues with no assigned_to
      - by_priority  : {priority_value: count, ...}
      - by_space     : list of (space_name, count) sorted desc
      - total        : total count
    """
    total = queryset.count()

    by_status = {}
    for row in queryset.values('status').annotate(n=Count('id')):
        by_status[row['status']] = row['n']

    assigned = queryset.filter(assigned_to__isnull=False).count()
    unassigned = total - assigned

    by_priority = {}
    for row in queryset.values('priority').annotate(n=Count('id')):
        by_priority[row['priority']] = row['n']

    by_space_qs = (
        queryset
        .values('space__name')
        .annotate(n=Count('id'))
        .order_by('-n')
    )
    by_space = [(r['space__name'] or 'No Space', r['n']) for r in by_space_qs]

    return {
        'total': total,
        'by_status': by_status,
        'assigned': assigned,
        'unassigned': unassigned,
        'by_priority': by_priority,
        'by_space': by_space,
    }


STATUS_LABELS = {
    'open': 'Open',
    'assigned': 'Assigned',
    'in_progress': 'In Progress',
    'resolved': 'Resolved',
    'escalated': 'Escalated',
    'closed': 'Closed',
    'cancelled': 'Cancelled',
}

STATUS_ORDER = ['open', 'assigned', 'in_progress', 'resolved', 'escalated', 'closed', 'cancelled']
PRIORITY_ORDER = ['critical', 'high', 'medium', 'low']

PRIORITY_LABELS = {
    'critical': 'Critical',
    'high': 'High',
    'medium': 'Medium',
    'low': 'Low',
}

ISSUE_TABLE_HEADERS = [
    'Ticket ID', 'Title', 'Status', 'Priority',
    'Reporter', 'Assigned To', 'Space', 'Created', 'Updated',
]


def _issue_rows(queryset):
    """Return list of row tuples for the ticket table."""
    rows = []
    for ticket in queryset.select_related('reporter', 'assigned_to', 'space'):
        reporter = ticket.reporter
        reporter_name = (
            reporter.get_full_name()
            or getattr(reporter, 'phone_number', None)
            or reporter.email
            or '—'
        )
        assignee = ticket.assigned_to
        if assignee:
            assignee_name = (
                assignee.get_full_name()
                or getattr(assignee, 'phone_number', None)
                or assignee.email
                or '—'
            )
        else:
            assignee_name = 'Unassigned'

        space_name = ticket.space.name if ticket.space else 'No Space'
        created = timezone.localtime(ticket.created_at).strftime('%Y-%m-%d')
        updated = timezone.localtime(ticket.updated_at).strftime('%Y-%m-%d')

        rows.append((
            ticket.ticket_id,
            ticket.title,
            STATUS_LABELS.get(ticket.status, ticket.status),
            PRIORITY_LABELS.get(ticket.priority, ticket.priority),
            reporter_name,
            assignee_name,
            space_name,
            created,
            updated,
        ))
    return rows


# ---------------------------------------------------------------------------
# Excel generator
# ---------------------------------------------------------------------------

_HEADER_FILL = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
_SUBHEADER_FILL = PatternFill(start_color='2E75B6', end_color='2E75B6', fill_type='solid')
_SUMMARY_LABEL_FILL = PatternFill(start_color='D6E4F0', end_color='D6E4F0', fill_type='solid')
_TABLE_HEADER_FILL = PatternFill(start_color='2E75B6', end_color='2E75B6', fill_type='solid')
_WHITE = Font(color='FFFFFF', bold=True)
_BOLD = Font(bold=True)


def _xl_cell(ws, row, col, value, *, bold=False, header=False, fill=None, wrap=False):
    cell = ws.cell(row=row, column=col, value=value)
    if header:
        cell.font = _WHITE
        cell.fill = fill or _HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=wrap)
    elif bold:
        cell.font = _BOLD
        if fill:
            cell.fill = fill
    if wrap and not header:
        cell.alignment = Alignment(wrap_text=True, vertical='top')
    return cell


def build_ticket_list_excel(queryset, filter_descriptions):
    """
    Build an Excel workbook with:
      Sheet 1 – Summary (filter info + counts)
      Sheet 2 – Tickets (table of matching issues)
    Returns a BytesIO buffer.
    """
    wb = Workbook()
    summary_ws = wb.active
    summary_ws.title = 'Summary'
    issue_ws = wb.create_sheet('Tickets')

    generated_at = timezone.now().strftime('%Y-%m-%d %H:%M')
    summary = _build_summary(queryset)

    # ---- Summary sheet -------------------------------------------------
    row = 1

    # Title
    summary_ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    _xl_cell(summary_ws, row, 1, 'Ticket List Report', bold=True, header=True,
             fill=_HEADER_FILL)
    summary_ws.row_dimensions[row].height = 22
    row += 1

    # Generated at
    summary_ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    summary_ws.cell(row=row, column=1, value=f'Generated: {generated_at}')
    row += 2

    # Applied filters
    summary_ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    _xl_cell(summary_ws, row, 1, 'Applied Filters', bold=True, header=True,
             fill=_SUBHEADER_FILL)
    row += 1
    for desc in filter_descriptions:
        summary_ws.cell(row=row, column=1, value=desc)
        row += 1
    row += 1

    # Total
    summary_ws.cell(row=row, column=1, value='Total Tickets')
    _xl_cell(summary_ws, row, 1, 'Total Tickets', bold=True, fill=_SUMMARY_LABEL_FILL)
    summary_ws.cell(row=row, column=2, value=summary['total'])
    row += 2

    # By status
    _xl_cell(summary_ws, row, 1, 'By Status', bold=True, header=True,
             fill=_SUBHEADER_FILL)
    _xl_cell(summary_ws, row, 2, 'Count', bold=True, header=True,
             fill=_SUBHEADER_FILL)
    row += 1
    for status in STATUS_ORDER:
        count = summary['by_status'].get(status, 0)
        _xl_cell(summary_ws, row, 1, STATUS_LABELS[status], bold=False,
                 fill=_SUMMARY_LABEL_FILL)
        summary_ws.cell(row=row, column=2, value=count)
        row += 1
    row += 1

    # Assigned vs unassigned
    _xl_cell(summary_ws, row, 1, 'Assignment', bold=True, header=True,
             fill=_SUBHEADER_FILL)
    _xl_cell(summary_ws, row, 2, 'Count', bold=True, header=True,
             fill=_SUBHEADER_FILL)
    row += 1
    _xl_cell(summary_ws, row, 1, 'Assigned', fill=_SUMMARY_LABEL_FILL)
    summary_ws.cell(row=row, column=2, value=summary['assigned'])
    row += 1
    _xl_cell(summary_ws, row, 1, 'Unassigned', fill=_SUMMARY_LABEL_FILL)
    summary_ws.cell(row=row, column=2, value=summary['unassigned'])
    row += 2

    # By priority
    _xl_cell(summary_ws, row, 1, 'By Priority', bold=True, header=True,
             fill=_SUBHEADER_FILL)
    _xl_cell(summary_ws, row, 2, 'Count', bold=True, header=True,
             fill=_SUBHEADER_FILL)
    row += 1
    for priority in PRIORITY_ORDER:
        count = summary['by_priority'].get(priority, 0)
        _xl_cell(summary_ws, row, 1, PRIORITY_LABELS[priority],
                 fill=_SUMMARY_LABEL_FILL)
        summary_ws.cell(row=row, column=2, value=count)
        row += 1
    row += 2

    # By space (top 10)
    _xl_cell(summary_ws, row, 1, 'By Space (top 10)', bold=True, header=True,
             fill=_SUBHEADER_FILL)
    _xl_cell(summary_ws, row, 2, 'Count', bold=True, header=True,
             fill=_SUBHEADER_FILL)
    row += 1
    for space_name, count in summary['by_space'][:10]:
        _xl_cell(summary_ws, row, 1, space_name, fill=_SUMMARY_LABEL_FILL)
        summary_ws.cell(row=row, column=2, value=count)
        row += 1

    # Column widths
    summary_ws.column_dimensions['A'].width = 28
    summary_ws.column_dimensions['B'].width = 14

    # ---- Tickets sheet --------------------------------------------------
    # Header row
    for col_idx, header in enumerate(ISSUE_TABLE_HEADERS, start=1):
        _xl_cell(issue_ws, 1, col_idx, header, bold=True, header=True,
                 fill=_TABLE_HEADER_FILL)

    rows = _issue_rows(queryset)
    if rows:
        for row_idx, row_data in enumerate(rows, start=2):
            for col_idx, value in enumerate(row_data, start=1):
                cell = issue_ws.cell(row=row_idx, column=col_idx, value=value)
                if col_idx == 2:  # Title
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
    else:
        issue_ws.merge_cells(start_row=2, start_column=1, end_row=2,
                             end_column=len(ISSUE_TABLE_HEADERS))
        issue_ws.cell(row=2, column=1,
                      value='No tickets match the selected filters.')

    # Column widths for issues sheet
    widths = [14, 40, 14, 12, 20, 20, 18, 12, 12]
    for col_idx, w in enumerate(widths, start=1):
        issue_ws.column_dimensions[
            issue_ws.cell(row=1, column=col_idx).column_letter
        ].width = w

    # Freeze header row
    issue_ws.freeze_panes = 'A2'

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# PDF generator
# ---------------------------------------------------------------------------

def build_ticket_list_pdf(queryset, filter_descriptions):
    """
    Build a landscape PDF report with:
      - Header (title, generated-at, filters, total)
      - Summary table (status / assignment / priority)
      - Ticket table
    Returns a BytesIO buffer.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        'SectionHead',
        parent=styles['Heading2'],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
    )
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
    )

    generated_at = timezone.now().strftime('%Y-%m-%d %H:%M')
    summary = _build_summary(queryset)

    story = []

    # ----- Title & metadata -----
    story.append(Paragraph('Ticket List Report', title_style))
    story.append(Paragraph(f'Generated: {generated_at}', body_style))
    story.append(Spacer(1, 0.1 * inch))

    # Applied filters
    story.append(Paragraph('<b>Applied Filters</b>', body_style))
    for desc in filter_descriptions:
        story.append(Paragraph(f'• {desc}', body_style))
    story.append(Paragraph(f'<b>Total Tickets: {summary["total"]}</b>', body_style))
    story.append(Spacer(1, 0.15 * inch))

    # ----- Summary tables -----
    story.append(Paragraph('Summary', section_style))

    _dark_blue = colors.HexColor('#1F4E79')
    _mid_blue = colors.HexColor('#2E75B6')
    _light_blue = colors.HexColor('#D6E4F0')

    def _summary_table(header_label, rows_data):
        """Small two-column table: label | count."""
        data = [[header_label, 'Count']] + rows_data
        t = Table(data, colWidths=[2.2 * inch, 0.8 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), _mid_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (0, -1), _light_blue),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EBF5FB')]),
        ]))
        return t

    # Status summary
    status_rows = [
        [STATUS_LABELS[s], summary['by_status'].get(s, 0)]
        for s in STATUS_ORDER
    ]
    # Assignment summary
    assignment_rows = [
        ['Assigned', summary['assigned']],
        ['Unassigned', summary['unassigned']],
    ]
    # Priority summary
    priority_rows = [
        [PRIORITY_LABELS[p], summary['by_priority'].get(p, 0)]
        for p in PRIORITY_ORDER
    ]

    # Lay out the three summary tables side-by-side
    status_tbl = _summary_table('Status', status_rows)
    assign_tbl = _summary_table('Assignment', assignment_rows)
    priority_tbl = _summary_table('Priority', priority_rows)

    side_by_side = Table(
        [[status_tbl, assign_tbl, priority_tbl]],
        colWidths=[3.2 * inch, 3.2 * inch, 3.2 * inch],
    )
    side_by_side.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(side_by_side)

    # Space summary (top 10)
    if summary['by_space']:
        story.append(Spacer(1, 0.1 * inch))
        space_rows = [[name, count] for name, count in summary['by_space'][:10]]
        story.append(_summary_table('Top Spaces', space_rows))

    story.append(Spacer(1, 0.2 * inch))

    # ----- Ticket table -----
    story.append(Paragraph('Tickets', section_style))

    issue_rows = _issue_rows(queryset)

    if issue_rows:
        # Build table data with header
        table_data = [ISSUE_TABLE_HEADERS] + [list(r) for r in issue_rows]
        # Wrap long strings in Paragraph for wrapping
        wrapped_data = []
        for r_idx, row in enumerate(table_data):
            wrapped_row = []
            for c_idx, cell in enumerate(row):
                if r_idx == 0:
                    wrapped_row.append(Paragraph(f'<b>{cell}</b>', small_style))
                elif c_idx == 1:  # Title column — allow wrapping
                    wrapped_row.append(Paragraph(str(cell), small_style))
                else:
                    wrapped_row.append(str(cell))
            wrapped_data.append(wrapped_row)

        col_widths = [
            0.95 * inch,  # Ticket ID
            2.8 * inch,   # Title
            0.85 * inch,  # Status
            0.75 * inch,  # Priority
            1.2 * inch,   # Reporter
            1.2 * inch,   # Assigned To
            1.1 * inch,   # Space
            0.85 * inch,  # Created
            0.85 * inch,  # Updated
        ]
        issue_table = Table(wrapped_data, colWidths=col_widths, repeatRows=1)
        issue_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), _dark_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#EBF5FB')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(issue_table)
    else:
        story.append(Paragraph('No tickets match the selected filters.', body_style))

    doc.build(story)
    buf.seek(0)
    return buf
