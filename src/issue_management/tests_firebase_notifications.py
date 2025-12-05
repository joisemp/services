"""
Tests for Firebase Cloud Messaging notifications
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock
from issue_management.utils.firebase_notifications import (
    send_push_notification,
    send_push_notification_to_multiple,
    send_issue_created_notification,
    _cleanup_invalid_tokens,
)
from firebase_admin import messaging


class FirebaseNotificationTests(TestCase):
    """Test Firebase push notification functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_token = "test_fcm_token_123"
        self.invalid_token = "invalid_token_456"
        self.title = "Test Notification"
        self.body = "This is a test notification"
        self.data = {'key': 'value'}
    
    @patch('issue_management.utils.firebase_notifications.firebase_admin._apps', [True])
    @patch('issue_management.utils.firebase_notifications.messaging.send')
    def test_send_single_notification_success(self, mock_send):
        """Test sending a single notification successfully"""
        mock_send.return_value = "message-id-123"
        
        result = send_push_notification(
            self.valid_token,
            self.title,
            self.body,
            self.data
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['response'], "message-id-123")
        self.assertIsNone(result['error'])
        mock_send.assert_called_once()
    
    @patch('issue_management.utils.firebase_notifications.firebase_admin._apps', [True])
    @patch('issue_management.utils.firebase_notifications.messaging.send')
    def test_send_notification_invalid_token(self, mock_send):
        """Test handling invalid FCM token"""
        mock_send.side_effect = messaging.UnregisteredError("Token not registered")
        
        result = send_push_notification(
            self.invalid_token,
            self.title,
            self.body
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Invalid or unregistered token')
    
    @patch('issue_management.utils.firebase_notifications.firebase_admin._apps', [])
    def test_send_notification_firebase_not_initialized(self):
        """Test sending notification when Firebase is not initialized"""
        result = send_push_notification(
            self.valid_token,
            self.title,
            self.body
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Firebase not initialized')
    
    def test_send_notification_no_token(self):
        """Test sending notification without token"""
        result = send_push_notification(
            None,
            self.title,
            self.body
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'No FCM token provided')
    
    @patch('issue_management.utils.firebase_notifications.firebase_admin._apps', [True])
    @patch('issue_management.utils.firebase_notifications.messaging.send')
    def test_high_priority_notification(self, mock_send):
        """Test sending high priority notification"""
        mock_send.return_value = "message-id-456"
        
        result = send_push_notification(
            self.valid_token,
            self.title,
            self.body,
            high_priority=True,
            ttl_hours=1
        )
        
        self.assertTrue(result['success'])
        # Verify the message was constructed with high priority settings
        call_args = mock_send.call_args[0][0]
        self.assertEqual(call_args.android.priority, 'high')
        self.assertEqual(call_args.apns.headers['apns-priority'], '10')
    
    @patch('issue_management.utils.firebase_notifications.firebase_admin._apps', [True])
    @patch('issue_management.utils.firebase_notifications.messaging.send_each_for_multicast')
    def test_batch_notification_success(self, mock_send_multicast):
        """Test sending batch notifications successfully"""
        tokens = [f"token_{i}" for i in range(10)]
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.success_count = 10
        mock_response.failure_count = 0
        mock_response.responses = [MagicMock(success=True) for _ in range(10)]
        mock_send_multicast.return_value = mock_response
        
        result = send_push_notification_to_multiple(
            tokens,
            self.title,
            self.body,
            self.data
        )
        
        self.assertEqual(result['success'], 10)
        self.assertEqual(result['failure'], 0)
        self.assertEqual(len(result['invalid_tokens']), 0)
    
    @patch('issue_management.utils.firebase_notifications.firebase_admin._apps', [True])
    @patch('issue_management.utils.firebase_notifications.messaging.send_each_for_multicast')
    def test_batch_notification_with_failures(self, mock_send_multicast):
        """Test batch notifications with some failures"""
        tokens = [f"token_{i}" for i in range(5)]
        
        # Mock mixed response (3 success, 2 failures)
        mock_response = MagicMock()
        mock_response.success_count = 3
        mock_response.failure_count = 2
        mock_response.responses = [
            MagicMock(success=True),
            MagicMock(success=True),
            MagicMock(success=False, exception=messaging.UnregisteredError("Invalid")),
            MagicMock(success=True),
            MagicMock(success=False, exception=messaging.UnregisteredError("Invalid")),
        ]
        mock_send_multicast.return_value = mock_response
        
        result = send_push_notification_to_multiple(
            tokens,
            self.title,
            self.body
        )
        
        self.assertEqual(result['success'], 3)
        self.assertEqual(result['failure'], 2)
        self.assertEqual(len(result['invalid_tokens']), 2)
        self.assertIn('token_2', result['invalid_tokens'])
        self.assertIn('token_4', result['invalid_tokens'])
    
    @patch('issue_management.utils.firebase_notifications.firebase_admin._apps', [True])
    @patch('issue_management.utils.firebase_notifications.messaging.send_each_for_multicast')
    def test_batch_large_token_list(self, mock_send_multicast):
        """Test batch notification with >500 tokens (multiple batches)"""
        tokens = [f"token_{i}" for i in range(750)]
        
        # Mock successful response for each batch
        mock_response = MagicMock()
        mock_response.success_count = 500
        mock_response.failure_count = 0
        mock_response.responses = [MagicMock(success=True) for _ in range(500)]
        
        mock_response2 = MagicMock()
        mock_response2.success_count = 250
        mock_response2.failure_count = 0
        mock_response2.responses = [MagicMock(success=True) for _ in range(250)]
        
        mock_send_multicast.side_effect = [mock_response, mock_response2]
        
        result = send_push_notification_to_multiple(
            tokens,
            self.title,
            self.body
        )
        
        self.assertEqual(result['success'], 750)
        self.assertEqual(result['failure'], 0)
        self.assertEqual(mock_send_multicast.call_count, 2)  # Two batches
    
    def test_batch_notification_empty_tokens(self):
        """Test batch notification with empty token list"""
        result = send_push_notification_to_multiple(
            [],
            self.title,
            self.body
        )
        
        self.assertEqual(result['success'], 0)
        self.assertEqual(result['failure'], 0)
    
    @patch('issue_management.utils.firebase_notifications.firebase_admin._apps', [True])
    @patch('issue_management.utils.firebase_notifications.messaging.send_each_for_multicast')
    def test_batch_notification_filters_empty_tokens(self, mock_send_multicast):
        """Test that empty/None tokens are filtered out"""
        tokens = ["token_1", None, "", "token_2", None]
        
        mock_response = MagicMock()
        mock_response.success_count = 2
        mock_response.failure_count = 0
        mock_response.responses = [MagicMock(success=True) for _ in range(2)]
        mock_send_multicast.return_value = mock_response
        
        result = send_push_notification_to_multiple(
            tokens,
            self.title,
            self.body
        )
        
        self.assertEqual(result['success'], 2)
        # Verify only valid tokens were sent
        call_args = mock_send_multicast.call_args[0][0]
        self.assertEqual(len(call_args.tokens), 2)
    
    @patch('issue_management.utils.firebase_notifications.send_push_notification_to_multiple')
    def test_issue_created_notification(self, mock_send_multiple):
        """Test sending issue created notification"""
        # Create mock issue
        mock_issue = MagicMock()
        mock_issue.id = 1
        mock_issue.slug = "test-issue-abc1"
        mock_issue.title = "Test Issue"
        mock_issue.priority = "high"
        mock_issue.status = "open"
        mock_issue.get_priority_display.return_value = "High"
        mock_issue.reporter.get_full_name.return_value = "John Doe"
        
        # Create mock admins
        mock_admin1 = MagicMock()
        mock_admin1.fcm_token = "admin_token_1"
        mock_admin2 = MagicMock()
        mock_admin2.fcm_token = "admin_token_2"
        
        mock_send_multiple.return_value = {
            'success': 2,
            'failure': 0,
            'invalid_tokens': []
        }
        
        result = send_issue_created_notification(
            mock_issue,
            [mock_admin1, mock_admin2]
        )
        
        self.assertEqual(result['success'], 2)
        self.assertEqual(result['failure'], 0)
        
        # Verify high priority was set for high priority issue
        call_kwargs = mock_send_multiple.call_args[1]
        self.assertTrue(call_kwargs['high_priority'])
    
    @patch('core.models.User')
    def test_cleanup_invalid_tokens(self, mock_user_model):
        """Test cleanup of invalid FCM tokens"""
        invalid_tokens = ["invalid_1", "invalid_2"]
        
        mock_queryset = MagicMock()
        mock_queryset.update.return_value = 2
        mock_user_model.objects.filter.return_value = mock_queryset
        
        _cleanup_invalid_tokens([], invalid_tokens)
        
        mock_user_model.objects.filter.assert_called_once_with(
            fcm_token__in=invalid_tokens
        )
        mock_queryset.update.assert_called_once_with(fcm_token=None)
    
    @patch('issue_management.utils.firebase_notifications.firebase_admin._apps', [True])
    @patch('issue_management.utils.firebase_notifications.messaging.send')
    def test_payload_size_warning(self, mock_send):
        """Test warning for large payload"""
        # Create very long title and body
        long_title = "A" * 2000
        long_body = "B" * 2000
        large_data = {f"key_{i}": "value" * 100 for i in range(50)}
        
        mock_send.return_value = "message-id"
        
        with self.assertLogs('issue_management.utils.firebase_notifications', level='WARNING') as cm:
            result = send_push_notification(
                self.valid_token,
                long_title,
                long_body,
                large_data
            )
            
            # Check that warning was logged
            self.assertTrue(any('may be too large' in log for log in cm.output))
