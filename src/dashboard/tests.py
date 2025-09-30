from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Organization, Space, User
from issue_management.models import Issue, WorkTask


class DashboardViewTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Acme Org')
		self.space_a = Space.objects.create(name='Building A', org=self.org)
		self.space_b = Space.objects.create(name='Building B', org=self.org)

		self.central_admin = User.objects.create_user(
			email='central@example.com',
			password='pass1234',
			user_type='central_admin',
			organization=self.org,
			first_name='Central',
			last_name='Admin',
		)

		self.space_admin = User.objects.create_user(
			email='space@example.com',
			password='pass1234',
			user_type='space_admin',
			organization=self.org,
			first_name='Space',
			last_name='Admin',
		)
		self.space_admin.spaces.add(self.space_a)

		self.reporter = User.objects.create_user(
			email='reporter@example.com',
			password='pass1234',
			user_type='supervisor',
			organization=self.org,
			first_name='Report',
			last_name='Er',
		)

		self._create_issues()

	def _create_issues(self):
		now = timezone.now()

		self.issue_open = Issue.objects.create(
			title='Water leak',
			description='Pipe leaking in basement',
			reporter=self.reporter,
			status='open',
			priority='medium',
			org=self.org,
			space=self.space_a,
		)

		self.issue_in_progress = Issue.objects.create(
			title='Broken elevator',
			description='Elevator stuck between floors',
			reporter=self.reporter,
			status='in_progress',
			priority='high',
			assigned_to=self.space_admin,
			org=self.org,
			space=self.space_a,
		)

		self.issue_resolved = Issue.objects.create(
			title='Lighting issue',
			description='Lights flickering on level 2',
			reporter=self.reporter,
			status='resolved',
			priority='low',
			org=self.org,
			space=self.space_a,
		)

		self.issue_other_space = Issue.objects.create(
			title='Parking gate stuck',
			description='Gate not closing properly',
			reporter=self.reporter,
			status='assigned',
			priority='medium',
			org=self.org,
			space=self.space_b,
		)

		WorkTask.objects.create(
			issue=self.issue_in_progress,
			title='Diagnose fault',
			description='Investigate mechanical failure',
			assigned_to=self.space_admin,
			due_date=now + timedelta(days=2),
		)

		WorkTask.objects.create(
			issue=self.issue_in_progress,
			title='Order replacement parts',
			description='Procure necessary parts',
			assigned_to=self.space_admin,
			due_date=now - timedelta(days=2),
		)

	def _summary_to_dict(self, summary_cards):
		return {card['label']: card['value'] for card in summary_cards}

	def test_central_admin_dashboard_aggregates_expected_data(self):
		self.client.force_login(self.central_admin)
		response = self.client.get(reverse('dashboard:central_admin_dashboard'))

		self.assertEqual(response.status_code, 200)
		summary_cards = response.context['summary_cards']
		summary_map = self._summary_to_dict(summary_cards)

		self.assertEqual(summary_map['Total Issues'], 4)
		self.assertEqual(summary_map['Active Issues'], 3)  # open, in progress, assigned
		self.assertEqual(summary_map['Resolved This Month'], 1)
		self.assertEqual(summary_map['Overdue Tasks'], 1)
		self.assertEqual(summary_map['Pending Tasks'], 2)

		status_breakdown = {item['status']: item['count'] for item in response.context['status_breakdown']}
		self.assertEqual(status_breakdown['open'], 1)
		self.assertEqual(status_breakdown['in_progress'], 1)
		self.assertEqual(status_breakdown['resolved'], 1)
		self.assertEqual(status_breakdown['assigned'], 1)

		priority_breakdown = {item['priority']: item['count'] for item in response.context['priority_breakdown']}
		self.assertEqual(priority_breakdown['high'], 1)
		self.assertEqual(priority_breakdown['medium'], 2)
		self.assertEqual(priority_breakdown['low'], 1)

		recent_issues = response.context['recent_issues']
		self.assertTrue(all('url' in issue for issue in recent_issues))
		self.assertGreaterEqual(len(recent_issues), 3)

	def test_space_admin_dashboard_limits_to_assigned_spaces(self):
		self.client.force_login(self.space_admin)
		response = self.client.get(reverse('dashboard:space_admin_dashboard'))

		self.assertEqual(response.status_code, 200)
		summary_cards = response.context['summary_cards']
		summary_map = self._summary_to_dict(summary_cards)

		# Only issues from space_a should be counted (3)
		self.assertEqual(summary_map['Total Issues'], 3)

		recent_issues = response.context['recent_issues']
		issue_titles = {issue['title'] for issue in recent_issues}
		self.assertIn('Water leak', issue_titles)
		self.assertNotIn('Parking gate stuck', issue_titles)

		self.assertEqual(response.context['view_all_issues_url'], reverse('issue_management:space_admin:issue_list'))
