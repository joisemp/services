# Firebase Push Notifications - Improvements & Best Practices

## Overview
The Firebase Cloud Messaging (FCM) notification system has been enhanced with production-ready improvements addressing FCM's limitations and best practices.

## Key Improvements

### 1. **Batch Sending (send_each_for_multicast)**
- **Before**: Sent notifications one-by-one (slow, inefficient)
- **After**: Uses `send_each_for_multicast()` for up to 500 tokens per batch
- **Benefit**: 10-100x faster for multiple recipients
- **Auto-batching**: Automatically splits large recipient lists into 500-token batches

```python
# Example: Send to 1000 users efficiently
result = send_push_notification_to_multiple(
    fcm_tokens=user_tokens,  # List of FCM tokens
    title="New Update Available",
    body="Check out the latest features",
    data={'update_id': '123'}
)
print(f"Success: {result['success']}, Failed: {result['failure']}")
```

### 2. **Invalid Token Cleanup**
- **Detection**: Identifies `UnregisteredError` and `SenderIdMismatchError`
- **Auto-cleanup**: Removes invalid tokens from database automatically
- **Benefit**: Maintains clean token database, reduces failed sends

```python
# Invalid tokens are automatically detected and removed
result = send_push_notification_to_multiple(tokens, title, body)
print(f"Cleaned up {len(result['invalid_tokens'])} invalid tokens")
```

### 3. **Priority & TTL Configuration**
- **High Priority**: For critical/urgent notifications
- **TTL (Time-to-Live)**: Configurable expiration (1-4 weeks)
- **Platform-specific**: Proper Android and iOS configurations

```python
# High priority notification with 1-hour TTL
result = send_push_notification(
    fcm_token=user.fcm_token,
    title="Critical Alert",
    body="Immediate action required",
    high_priority=True,  # Wakes device, bypasses battery optimization
    ttl_hours=1          # Expires after 1 hour
)
```

### 4. **Payload Size Validation**
- **4KB FCM Limit**: Automatic size validation
- **Warning Logs**: Alerts when payload approaches limit
- **Auto-truncation**: Title/body limits in helper functions

```python
# Automatically truncates to safe limits
title = f"New Issue: {issue.title[:80]}"  # Max 80 chars
body = f"Details: {issue.description[:200]}"  # Max 200 chars
```

### 5. **Enhanced Error Handling**
- **Detailed responses**: Returns success/failure with error details
- **Error categorization**: Distinguishes invalid tokens from transient errors
- **Comprehensive logging**: All errors logged with context

```python
result = send_push_notification(token, title, body)
if not result['success']:
    print(f"Failed: {result['error']}")
    if result['error'] == 'Invalid or unregistered token':
        # Token should be removed from database
        user.fcm_token = None
        user.save()
```

## API Reference

### `send_push_notification()`
Send notification to a single device.

```python
def send_push_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: dict = None,
    high_priority: bool = False,
    ttl_hours: int = 24
) -> dict
```

**Parameters:**
- `fcm_token`: FCM device token
- `title`: Notification title (keep under 100 chars)
- `body`: Notification body (keep under 200 chars)
- `data`: Custom data payload (optional)
- `high_priority`: High priority delivery (default: False)
- `ttl_hours`: Time-to-live in hours (default: 24)

**Returns:**
```python
{
    'success': bool,       # True if sent successfully
    'response': str,       # Message ID from FCM (if success)
    'error': str or None   # Error message (if failure)
}
```

**Error Types:**
- `'Firebase not initialized'`: Firebase SDK not configured
- `'No FCM token provided'`: Missing/empty token
- `'Invalid or unregistered token'`: Token needs cleanup
- `'Sender ID mismatch'`: Token from different Firebase project
- Other exceptions: Network errors, quota exceeded, etc.

### `send_push_notification_to_multiple()`
Send notification to multiple devices using batch API.

```python
def send_push_notification_to_multiple(
    fcm_tokens: list,
    title: str,
    body: str,
    data: dict = None,
    high_priority: bool = False,
    ttl_hours: int = 24
) -> dict
```

**Parameters:**
- `fcm_tokens`: List of FCM tokens (no limit, auto-batched)
- Other parameters: Same as `send_push_notification()`

**Returns:**
```python
{
    'success': int,           # Number of successful sends
    'failure': int,           # Number of failed sends
    'invalid_tokens': list    # List of invalid tokens (needs cleanup)
}
```

**Features:**
- Auto-batches into 500-token chunks (FCM limit)
- Processes all batches automatically
- Identifies invalid tokens for cleanup
- Returns aggregate results

### `send_issue_created_notification()`
Helper for issue creation notifications.

```python
def send_issue_created_notification(issue, central_admins) -> dict
```

**Features:**
- Automatically determines priority based on issue priority
- Truncates title/body to safe limits
- Includes issue metadata in data payload
- Auto-cleans invalid tokens
- 48-hour TTL for issue notifications

**Usage:**
```python
from core.models import User
from issue_management.utils.firebase_notifications import send_issue_created_notification

# Get admins
admins = User.objects.filter(user_type='central_admin', fcm_token__isnull=False)

# Send notification
result = send_issue_created_notification(issue, admins)
print(f"Notified {result['success']} admins")
```

## Best Practices

### 1. **Choose Appropriate Priority**
```python
# Use high priority for:
- Critical alerts requiring immediate attention
- Time-sensitive notifications (OTPs, alerts)
- Issues marked as "critical" or "high" priority

# Use normal priority for:
- General updates and informational messages
- Non-urgent notifications
- Marketing/promotional content
```

### 2. **Set Appropriate TTL**
```python
# Short TTL (1-6 hours):
- Time-sensitive alerts
- OTP codes
- Real-time updates

# Medium TTL (24-48 hours):
- Issue notifications
- Task assignments
- Important updates

# Long TTL (1-2 weeks):
- General announcements
- Non-urgent reminders
- Marketing messages
```

### 3. **Keep Payload Small**
```python
# DO: Keep data minimal
data = {
    'issue_id': '123',
    'type': 'issue_created'
}

# DON'T: Include large data
data = {
    'issue_full_details': {...},  # Too large!
    'entire_issue_object': {...}   # Way too large!
}

# Instead: Send minimal data and fetch details via API
```

### 4. **Handle Invalid Tokens**
```python
result = send_push_notification_to_multiple(tokens, title, body)

# Clean up invalid tokens
if result['invalid_tokens']:
    User.objects.filter(
        fcm_token__in=result['invalid_tokens']
    ).update(fcm_token=None)
```

### 5. **Batch for Efficiency**
```python
# DO: Use batch sending for multiple recipients
if len(tokens) > 1:
    send_push_notification_to_multiple(tokens, title, body)

# DON'T: Loop and send individually
for token in tokens:  # Slow!
    send_push_notification(token, title, body)
```

## Testing

Run the test suite:
```bash
# Inside Docker container
docker exec -it sfs-services-dev-container python manage.py test issue_management.tests_firebase_notifications

# Or run specific test
docker exec -it sfs-services-dev-container python manage.py test issue_management.tests_firebase_notifications.FirebaseNotificationTests.test_batch_notification_success
```

## Monitoring & Debugging

### Check Firebase Console
1. Go to Firebase Console → Cloud Messaging
2. View message delivery statistics
3. Monitor quota usage
4. Check for errors

### Application Logs
```python
import logging
logger = logging.getLogger('issue_management.utils.firebase_notifications')

# Check logs for:
# - "Successfully sent push notification" (success)
# - "Invalid/unregistered token detected" (token cleanup needed)
# - "Failed to send push notification" (errors)
# - "Notification payload may be too large" (size warning)
```

### Common Issues

**Issue**: Notifications not received
- **Check**: Is FCM token saved in database?
- **Check**: Is Firebase initialized? (check app logs)
- **Check**: Are notification permissions granted on device?
- **Check**: Is the token still valid?

**Issue**: High failure rate
- **Solution**: Check `invalid_tokens` in response and clean database
- **Solution**: Verify Firebase credentials are correct
- **Solution**: Check FCM quota in Firebase Console

**Issue**: Slow delivery for many recipients
- **Solution**: Ensure using `send_push_notification_to_multiple()` (batch API)
- **Solution**: Check network connectivity and Firebase service status

## FCM Limitations Reference

| Limitation | Value | Impact |
|------------|-------|--------|
| Payload size | 4KB max | Truncate data, use IDs instead of full objects |
| Batch size | 500 tokens | Auto-handled by our implementation |
| Topics per app | 2000 max | Plan topic structure carefully |
| Subscriptions per topic | 1M max | Should not be an issue for most apps |
| Message TTL | 4 weeks max | Set appropriate expiration |
| Delivery guarantee | Best-effort | Not 100% guaranteed, handle gracefully |

## Migration Notes

If you have existing code using the old API:

**Before:**
```python
result = send_push_notification_to_multiple(tokens, title, body)
# Returns: {'success': int, 'failure': int}
```

**After:**
```python
result = send_push_notification_to_multiple(tokens, title, body)
# Returns: {'success': int, 'failure': int, 'invalid_tokens': list}

# Handle invalid tokens
if result['invalid_tokens']:
    # Clean up database
    pass
```

## Additional Resources

- [Firebase Cloud Messaging Documentation](https://firebase.google.com/docs/cloud-messaging)
- [FCM Best Practices](https://firebase.google.com/docs/cloud-messaging/concept-options)
- [FCM HTTP v1 API](https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages)
- [Firebase Admin Python SDK](https://firebase.google.com/docs/reference/admin/python)
