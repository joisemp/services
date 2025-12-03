# Notification Feature Troubleshooting

## Changes Made

### 1. Fixed Firebase Configuration Access
- **Issue**: `FIREBASE_PROJECT_ID` was not accessible as a direct setting
- **Fix**: Added `FIREBASE_PROJECT_ID` as a standalone setting in `settings.py`
- **Status**: ✅ FIXED - API endpoint now returns proper config

### 2. Fixed Service Worker Scope
- **Issue**: Service worker was served from `/static/js/` which limits its scope
- **Fix**: Created `ServiceWorkerView` to serve from root path `/firebase-messaging-sw.js`
- **Status**: ✅ FIXED - Service worker now has full site scope

### 3. Updated Service Worker Registration
- **Issue**: FCM token manager was looking for service worker in wrong scope
- **Fix**: Updated registration paths from `/static/js/` to `/` (root)
- **Status**: ✅ FIXED

## Testing Steps

### 1. Clear Browser Cache & Service Workers
Open DevTools (F12) → Application tab → Service Workers → Click "Unregister" on all service workers

### 2. Reload the Page
Hard reload: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

### 3. Check Console for Initialization
You should see these logs in order:
```
Fetching Firebase config...
Fetched Firebase config: {apiKey: "...", ...}
Firebase config loaded successfully
Firebase Messaging initialized successfully
Registering service worker...
Service Worker registered successfully
Sending Firebase config to service worker
Requesting notification permission...
```

### 4. Grant Notification Permission
- Browser will prompt: "Allow notifications?"
- Click **Allow**
- Console should show:
```
Notification permission granted
Permission granted, getting FCM token...
FCM Token retrieved: <long-token-string>
FCM token registered successfully with backend
FCM initialization complete!
```

### 5. Test Notification
Create a new issue or trigger any notification event. You should receive a notification.

## Common Issues & Solutions

### Issue: "Failed to fetch Firebase configuration"
**Check**:
- `.env` file has all Firebase variables set
- Django server is running
- No errors in Django console

**Solution**: Verify environment variables are loaded:
```bash
docker exec -it sfs-services-dev-container python manage.py shell
>>> from django.conf import settings
>>> settings.FIREBASE_PROJECT_ID
'sfs-services'  # Should show your project ID
```

### Issue: "Service worker registration not found"
**Check**:
- Service worker registered successfully
- Browser DevTools → Application → Service Workers shows active worker

**Solution**:
1. Unregister all service workers
2. Hard reload page
3. Check if `/firebase-messaging-sw.js` is accessible

### Issue: "No FCM token available"
**Causes**:
- Notification permission denied
- Service worker not active
- VAPID key missing or incorrect

**Solution**:
1. Check browser notification permissions (Settings → Site settings)
2. Verify VAPID key in `.env` matches Firebase Console
3. Ensure service worker is active

### Issue: Notifications not received
**Check**:
1. FCM token saved in user profile:
   ```python
   # In Django shell
   from core.models import User
   user = User.objects.get(email='your@email.com')
   print(user.fcm_token)  # Should show token
   ```

2. Backend sending notifications:
   - Check Django logs for notification sending
   - Verify `send_push_notification()` is called

3. Firebase Admin SDK initialized:
   - Check for "Firebase Admin SDK initialized successfully" in logs
   - Verify credentials in `.env` are correct

## Quick Test Command

Test if Firebase config endpoint works:
```bash
curl http://localhost:7000/core/api/firebase-config/
```

Should return JSON with all Firebase config values.

Test if service worker is accessible:
```bash
curl http://localhost:7000/firebase-messaging-sw.js
```

Should return JavaScript code with proper Content-Type.

## Manual Notification Test

Send a test notification from Django shell:
```python
docker exec -it sfs-services-dev-container python manage.py shell

# In shell:
from issue_management.utils.firebase_notifications import send_push_notification
from core.models import User

# Get a user with FCM token
user = User.objects.filter(fcm_token__isnull=False).first()
print(f"Testing with user: {user.email}")
print(f"FCM Token: {user.fcm_token[:50]}...")

# Send test notification
result = send_push_notification(
    fcm_token=user.fcm_token,
    title="Test Notification",
    body="This is a test notification from Django shell",
    data={'test': 'true'}
)

print(f"Result: {result}")
```

## Browser Compatibility

**Supported**:
- Chrome/Edge (desktop & mobile)
- Firefox (desktop & mobile)
- Safari 16.4+ (desktop & mobile with iOS 16.4+)

**Not Supported**:
- Safari versions < 16.4
- Internet Explorer

## Next Steps

1. ✅ Firebase config endpoint working
2. ✅ Service worker served from root with correct scope
3. ✅ Service worker registration updated
4. 🔄 **ACTION REQUIRED**: Clear browser cache and test
5. 🔄 **ACTION REQUIRED**: Grant notification permission when prompted
6. 🔄 **ACTION REQUIRED**: Create test issue to verify notifications

## Files Modified

1. `src/config/settings.py` - Added `FIREBASE_PROJECT_ID` setting
2. `src/config/views.py` - Added `ServiceWorkerView` 
3. `src/config/urls.py` - Added route for service worker
4. `src/static/js/fcm-token-manager.js` - Updated service worker paths

All changes are backwards compatible and follow Django best practices.
