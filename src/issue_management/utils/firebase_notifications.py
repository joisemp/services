"""
Firebase Cloud Messaging (FCM) utility for sending push notifications
"""
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (singleton pattern)
def initialize_firebase():
    """Initialize Firebase Admin SDK if not already initialized"""
    if not firebase_admin._apps:
        try:
            # Check if Firebase credentials are configured
            if hasattr(settings, 'FIREBASE_CREDENTIALS') and settings.FIREBASE_CREDENTIALS:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.warning("Firebase credentials not configured. Push notifications disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")


def send_push_notification(fcm_token, title, body, data=None, high_priority=False, ttl_hours=24):
    """
    Send a push notification to a specific device
    
    Args:
        fcm_token (str): The FCM token of the device
        title (str): Notification title (max ~100 chars recommended)
        body (str): Notification body (max ~200 chars recommended)
        data (dict): Additional data to send with the notification
        high_priority (bool): Whether to send as high priority (default: False)
        ttl_hours (int): Time to live in hours (default: 24)
    
    Returns:
        dict: {'success': bool, 'response': str or None, 'error': str or None}
    """
    initialize_firebase()
    
    if not firebase_admin._apps:
        logger.warning("Firebase not initialized. Cannot send push notification.")
        return {'success': False, 'response': None, 'error': 'Firebase not initialized'}
    
    if not fcm_token:
        logger.warning("No FCM token provided. Cannot send push notification.")
        return {'success': False, 'response': None, 'error': 'No FCM token provided'}
    
    # Validate payload size (rough estimate: 4KB limit)
    estimated_size = len(title) + len(body) + len(str(data or {}))
    if estimated_size > 3500:  # Leave buffer for headers
        logger.warning(f"Notification payload may be too large (~{estimated_size} bytes)")
    
    try:
        # Configure Android-specific options
        android_config = messaging.AndroidConfig(
            priority='high' if high_priority else 'normal',
            ttl=timedelta(hours=ttl_hours),
            notification=messaging.AndroidNotification(
                sound='default',
                priority='high' if high_priority else 'default',
            )
        )
        
        # Configure iOS-specific options
        apns_config = messaging.APNSConfig(
            headers={
                'apns-priority': '10' if high_priority else '5',
            },
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    sound='default',
                    content_available=True,
                ),
            ),
        )
        
        # Construct the message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
            android=android_config,
            apns=apns_config,
        )
        
        # Send the message
        response = messaging.send(message)
        logger.info(f"Successfully sent push notification: {response}")
        return {'success': True, 'response': response, 'error': None}
        
    except messaging.UnregisteredError:
        logger.warning(f"FCM token is invalid or unregistered: {fcm_token[:20]}...")
        return {'success': False, 'response': None, 'error': 'Invalid or unregistered token'}
    except messaging.SenderIdMismatchError:
        logger.error(f"FCM token sender ID mismatch: {fcm_token[:20]}...")
        return {'success': False, 'response': None, 'error': 'Sender ID mismatch'}
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return {'success': False, 'response': None, 'error': str(e)}


def send_push_notification_to_multiple(fcm_tokens, title, body, data=None, high_priority=False, ttl_hours=24):
    """
    Send a push notification to multiple devices using batch API
    
    Args:
        fcm_tokens (list): List of FCM tokens (max 500 per batch)
        title (str): Notification title (max ~100 chars recommended)
        body (str): Notification body (max ~200 chars recommended)
        data (dict): Additional data to send with the notification
        high_priority (bool): Whether to send as high priority (default: False)
        ttl_hours (int): Time to live in hours (default: 24)
    
    Returns:
        dict: {
            'success': int,           # Number of successful sends
            'failure': int,           # Number of failed sends
            'invalid_tokens': list    # List of invalid tokens to remove from DB
        }
    """
    initialize_firebase()
    
    if not firebase_admin._apps:
        logger.warning("Firebase not initialized. Cannot send push notifications.")
        return {'success': 0, 'failure': len(fcm_tokens), 'invalid_tokens': []}
    
    if not fcm_tokens:
        logger.warning("No FCM tokens provided. Cannot send push notifications.")
        return {'success': 0, 'failure': 0, 'invalid_tokens': []}
    
    # Filter out None/empty tokens
    valid_tokens = [token for token in fcm_tokens if token]
    
    if not valid_tokens:
        logger.warning("No valid FCM tokens. Cannot send push notifications.")
        return {'success': 0, 'failure': 0, 'invalid_tokens': []}
    
    # Validate payload size
    estimated_size = len(title) + len(body) + len(str(data or {}))
    if estimated_size > 3500:
        logger.warning(f"Notification payload may be too large (~{estimated_size} bytes)")
    
    # Configure Android-specific options
    android_config = messaging.AndroidConfig(
        priority='high' if high_priority else 'normal',
        ttl=timedelta(hours=ttl_hours),
        notification=messaging.AndroidNotification(
            sound='default',
            priority='high' if high_priority else 'default',
        )
    )
    
    # Configure iOS-specific options
    apns_config = messaging.APNSConfig(
        headers={
            'apns-priority': '10' if high_priority else '5',
        },
        payload=messaging.APNSPayload(
            aps=messaging.Aps(
                alert=messaging.ApsAlert(
                    title=title,
                    body=body,
                ),
                sound='default',
                content_available=True,
            ),
        ),
    )
    
    success_count = 0
    failure_count = 0
    invalid_tokens = []
    
    # Process tokens in batches of 500 (FCM limit)
    batch_size = 500
    for i in range(0, len(valid_tokens), batch_size):
        batch_tokens = valid_tokens[i:i + batch_size]
        
        try:
            # Create multicast message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                tokens=batch_tokens,
                android=android_config,
                apns=apns_config,
            )
            
            # Send to multiple devices (using send_each_for_multicast)
            response = messaging.send_each_for_multicast(message)
            
            success_count += response.success_count
            failure_count += response.failure_count
            
            # Process responses to identify invalid tokens
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        token = batch_tokens[idx]
                        error = resp.exception
                        
                        # Check if token is invalid/unregistered
                        if isinstance(error, (messaging.UnregisteredError, messaging.SenderIdMismatchError)):
                            invalid_tokens.append(token)
                            logger.warning(f"Invalid/unregistered token detected: {token[:20]}...")
                        else:
                            logger.error(f"Failed to send to token {token[:20]}...: {error}")
            
            logger.info(f"Batch {i//batch_size + 1}: Sent {response.success_count} successfully, {response.failure_count} failed")
            
        except Exception as e:
            logger.error(f"Failed to send batch {i//batch_size + 1}: {e}")
            failure_count += len(batch_tokens)
    
    logger.info(f"Total: {success_count} successful, {failure_count} failed, {len(invalid_tokens)} invalid tokens")
    
    return {
        'success': success_count,
        'failure': failure_count,
        'invalid_tokens': invalid_tokens
    }


def send_issue_created_notification(issue, central_admins):
    """
    Send notification to central admins when a new issue is created
    
    Args:
        issue: The Issue model instance
        central_admins: QuerySet or list of User instances with user_type='central_admin'
    
    Returns:
        dict: {
            'success': int,
            'failure': int,
            'invalid_tokens': list
        }
    """
    # Get FCM tokens from central admins
    fcm_tokens = [admin.fcm_token for admin in central_admins if admin.fcm_token]
    
    if not fcm_tokens:
        logger.info("No central admins with FCM tokens found")
        return {'success': 0, 'failure': 0, 'invalid_tokens': []}
    
    # Prepare notification content (keep within size limits)
    title = f"New Issue: {issue.title[:80]}"  # Limit title length
    reporter_name = issue.reporter.get_full_name() or issue.reporter.phone_number
    body = f"Priority: {issue.get_priority_display()} | Reporter: {reporter_name[:50]}"[:200]  # Limit body
    
    # Additional data for the notification
    data = {
        'issue_id': str(issue.id),
        'issue_slug': issue.slug,
        'priority': issue.priority,
        'status': issue.status,
        'notification_type': 'issue_created'
    }
    
    # Send high-priority notifications for critical issues
    is_high_priority = issue.priority in ['critical', 'high']
    
    # Send notifications
    result = send_push_notification_to_multiple(
        fcm_tokens, 
        title, 
        body, 
        data,
        high_priority=is_high_priority,
        ttl_hours=48  # Keep for 48 hours
    )
    
    # Clean up invalid tokens from database
    if result.get('invalid_tokens'):
        _cleanup_invalid_tokens(central_admins, result['invalid_tokens'])
    
    return result


def _cleanup_invalid_tokens(users, invalid_tokens):
    """
    Remove invalid FCM tokens from user records
    
    Args:
        users: QuerySet or list of User instances
        invalid_tokens: List of invalid token strings
    """
    if not invalid_tokens:
        return
    
    try:
        # Import here to avoid circular imports
        from core.models import User
        
        # Remove invalid tokens
        updated = User.objects.filter(
            fcm_token__in=invalid_tokens
        ).update(fcm_token=None)
        
        logger.info(f"Cleaned up {updated} invalid FCM tokens from database")
        
    except Exception as e:
        logger.error(f"Failed to cleanup invalid tokens: {e}")
