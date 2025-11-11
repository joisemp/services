# Performance Report Feature - Quick Start Guide

## What is it?
A PDF report generation feature that provides performance insights and ratings (0-100) for Supervisors and Maintainers based on their work with issues and tasks.

## How to Access
1. Log in as a **Central Admin**
2. Click **"Performance Report"** in the sidebar (between "Site Visits" and "Spaces")
3. Configure your report settings
4. Click **"Generate PDF Report"**
5. The PDF will automatically download

## Report Configuration Options

### 1. Report Period
Choose the time period for the report:
- **Last 7 Days**: Quick snapshot of recent activity
- **Last 30 Days**: Standard monthly review (default)
- **Last 90 Days**: Quarterly assessment
- **Custom Date Range**: Pick any start and end date

### 2. Include Roles
Select which user types to include:
- ✅ **Include Supervisors**: Show supervisor performance metrics
- ✅ **Include Maintainers**: Show maintainer performance metrics
- Both are selected by default

### 3. Specific Users (Optional)
- Leave unchecked to include **all users** of selected roles
- Check specific users to generate a **focused report** for only those users
- Useful for individual performance reviews

## What's in the Report?

### For Supervisors:
- **Issues assigned, resolved, in-progress, pending**
- **Work tasks created** (shows proactive management)
- **Site visits coordinated**
- **Average resolution time** (in hours)
- **Performance rating (0-100)** based on:
  - How many issues they resolve (40%)
  - How quickly they resolve them (30%)
  - How many tasks they create (20%)
  - Site visit coordination (10%)

### For Maintainers:
- **Tasks assigned, completed, pending**
- **Site visits assigned, completed, pending**
- **Average task completion time** (in hours)
- **Issues contributed to** (breadth of work)
- **Performance rating (0-100)** based on:
  - Task completion rate (50%)
  - Speed of completion (30%)
  - Site visit participation (15%)
  - Issue contribution (5%)

### Rating Scale:
- **90-100**: 🟢 Excellent
- **75-89**: 🔵 Good
- **60-74**: 🟡 Satisfactory
- **40-59**: 🟠 Needs Improvement
- **0-39**: 🔴 Poor

### Summary Section:
- **Total user counts** per role
- **Average ratings** per role
- **Top performers** list (top 3 from each category)

## Example Use Cases

### Monthly Team Review
```
Period: Last 30 Days
Include: ✅ Supervisors ✅ Maintainers
Users: (all)
```
Perfect for regular team performance reviews.

### Quarterly Manager Assessment
```
Period: Last 90 Days
Include: ✅ Supervisors ⬜ Maintainers
Users: (all)
```
Focus on supervisor performance over the quarter.

### Individual Performance Review
```
Period: Custom (e.g., Jan 1 - Mar 31)
Include: ✅ Supervisors ✅ Maintainers
Users: ✅ John Doe
```
Generate a focused report for a specific employee.

### Quick Weekly Check
```
Period: Last 7 Days
Include: ✅ Supervisors ✅ Maintainers
Users: (all)
```
Quick snapshot of recent team activity.

## Tips for Best Results

1. **Regular Generation**: Generate reports monthly for consistent tracking
2. **Compare Periods**: Run reports for different periods to see trends
3. **Fair Assessment**: Consider the rating as one factor among many
4. **Context Matters**: Low ratings may reflect low activity, not poor performance
5. **Use for Development**: Identify areas where team members need support
6. **Celebrate Success**: Recognize top performers

## Troubleshooting

### "No users found"
- Ensure supervisors/maintainers exist in your organization
- Check that users are marked as active
- Verify you've selected at least one role

### "Failed to generate report"
- Check your date range (end date must be after start date)
- Ensure reportlab is installed in the container
- Check Django logs for detailed error messages

### Empty Report
- Users may have no activity in the selected period
- Try a longer date range
- Verify that issues and tasks exist in the system

## Technical Notes

- Reports are generated on-demand (not cached)
- Generation typically takes 1-3 seconds
- PDF filename format: `performance_report_YYYYMMDD_HHMMSS.pdf`
- Reports use data from the Issue Management system only

## Need Help?

Refer to the full documentation at `docs/PERFORMANCE_REPORT_FEATURE.md` for:
- Detailed rating calculation methodology
- Technical implementation details
- Testing recommendations
- Future enhancement ideas

---

**Created for**: Central Admin Role  
**Last Updated**: November 2025  
**Django Version**: 5.2
