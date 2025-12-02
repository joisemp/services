"""
Firebase Cloud Messaging (FCM) utility for sending push notifications
"""
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import logging

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


def send_push_notification(fcm_token, title, body, data=None):
    """
    Send a push notification to a specific device
    
    Args:
        fcm_token (str): The FCM token of the device
        title (str): Notification title
        body (str): Notification body
        data (dict): Additional data to send with the notification
    
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    initialize_firebase()
    
    if not firebase_admin._apps:
        logger.warning("Firebase not initialized. Cannot send push notification.")
        return False
    
    if not fcm_token:
        logger.warning("No FCM token provided. Cannot send push notification.")
        return False
    
    try:
        # Construct the message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
        )
        
        # Send the message
        response = messaging.send(message)
        logger.info(f"Successfully sent push notification: {response}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False


def send_push_notification_to_multiple(fcm_tokens, title, body, data=None):
    """
    Send a push notification to multiple devices
    
    Args:
        fcm_tokens (list): List of FCM tokens
        title (str): Notification title
        body (str): Notification body
        data (dict): Additional data to send with the notification
    
    Returns:
        dict: Dictionary with success and failure counts
    """
    initialize_firebase()
    
    if not firebase_admin._apps:
        logger.warning("Firebase not initialized. Cannot send push notifications.")
        return {'success': 0, 'failure': len(fcm_tokens)}
    
    if not fcm_tokens:
        logger.warning("No FCM tokens provided. Cannot send push notifications.")
        return {'success': 0, 'failure': 0}
    
    # Filter out None/empty tokens
    valid_tokens = [token for token in fcm_tokens if token]
    
    if not valid_tokens:
        logger.warning("No valid FCM tokens. Cannot send push notifications.")
        return {'success': 0, 'failure': 0}
    
    try:
        # Send to each device individually
        success_count = 0
        failure_count = 0
        
        for token in valid_tokens:
            try:
                # Construct the message for each token
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data or {},
                    token=token,
                )
                
                # Send the notification
                messaging.send(message)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send notification to token {token[:20]}...: {e}")
                failure_count += 1
        
        logger.info(f"Successfully sent {success_count} notifications, {failure_count} failed")
        
        return {
            'success': success_count,
            'failure': failure_count
        }
        
    except Exception as e:
        logger.error(f"Failed to send push notifications: {e}")
        return {'success': 0, 'failure': len(valid_tokens)}


def send_issue_created_notification(issue, central_admins):
    """
    Send notification to central admins when a new issue is created
    
    Args:
        issue: The Issue model instance
        central_admins: QuerySet or list of User instances with user_type='central_admin'
    
    Returns:
        dict: Dictionary with success and failure counts
    """
    # Get FCM tokens from central admins
    fcm_tokens = [admin.fcm_token for admin in central_admins if admin.fcm_token]
    
    if not fcm_tokens:
        logger.info("No central admins with FCM tokens found")
        return {'success': 0, 'failure': 0}
    
    # Prepare notification content
    title = f"New Issue: {issue.title}"
    body = f"Priority: {issue.get_priority_display()} | Reporter: {issue.reporter.get_full_name() or issue.reporter.phone_number}"
    
    # Additional data for the notification
    data = {
        'issue_id': str(issue.id),
        'issue_slug': issue.slug,
        'priority': issue.priority,
        'status': issue.status,
        'notification_type': 'issue_created'
    }
    
    # Send notifications
    return send_push_notification_to_multiple(fcm_tokens, title, body, data)
