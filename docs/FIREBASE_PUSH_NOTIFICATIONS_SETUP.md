# Firebase Push Notifications Setup Guide

## Overview
This guide will help you set up Firebase Cloud Messaging (FCM) for push notifications when issues are created in the system. Central admins in the organization will receive push notifications on their devices.

## Prerequisites
1. A Firebase account (free tier is sufficient)
2. A web browser for Firebase Console
3. Your Django application running

## Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add Project" or "Create a project"
3. Enter a project name (e.g., "Services Issue Tracker")
4. Disable Google Analytics (optional for push notifications)
5. Click "Create Project"

## Step 2: Register Your Web App

1. In Firebase Console, click the **Web icon** (`</>`) to add a web app
2. Enter an app nickname (e.g., "Services Web App")
3. Check "Also set up Firebase Hosting" (optional)
4. Click "Register app"
5. **Copy the Firebase configuration** - you'll need these values:
   ```javascript
   const firebaseConfig = {
     apiKey: "AIzaSy...",
     authDomain: "your-project.firebaseapp.com",
     projectId: "your-project-id",
     storageBucket: "your-project.appspot.com",
     messagingSenderId: "123456789",
     appId: "1:123456789:web:abc123..."
   };
   ```

## Step 3: Enable Cloud Messaging

1. In Firebase Console, go to **Project Settings** (gear icon)
2. Navigate to the **Cloud Messaging** tab
3. Under "Web configuration", find the **Web Push certificates** section
4. Click "Generate key pair" to create a VAPID key
5. **Copy the VAPID key** - you'll need this for the frontend

## Step 4: Generate Service Account Key (for Backend)

1. In Firebase Console, go to **Project Settings** > **Service Accounts**
2. Click "Generate new private key"
3. Click "Generate key" in the confirmation dialog
4. A JSON file will be downloaded - **save this securely**
5. Move this file to your project (recommended: `src/config/firebase-service-account.json`)
6. **IMPORTANT**: Add this file to `.gitignore` to keep it private

## Step 5: Update Environment Configuration

Add the following Firebase configuration to your `src/config/.env` file:

```env
# Firebase Cloud Messaging Configuration (Backend - Service Account)
FIREBASE_CREDENTIALS_PATH=/app/config/firebase-service-account.json

# Firebase Web Configuration (Frontend - Public Config)
FIREBASE_API_KEY=AIzaSy...                                    # From Step 2
FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com          # From Step 2
FIREBASE_PROJECT_ID=your-project-id                           # From Step 2
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com           # From Step 2
FIREBASE_MESSAGING_SENDER_ID=123456789                        # From Step 2
FIREBASE_APP_ID=1:123456789:web:abc123...                     # From Step 2
FIREBASE_VAPID_KEY=BNcE8xF...                                 # From Step 3
```

**Notes:**
- All Firebase web config values come from Step 2 (Firebase config object)
- `FIREBASE_VAPID_KEY` comes from Step 3 (Web Push certificate)
- `FIREBASE_CREDENTIALS_PATH` should use the Docker container path if using Docker

## Step 6: Configure Service Account File Path

## Step 6: Configure Service Account File Path

If using Docker, you need to make the service account file accessible to the container.

### Option A: Mount as volume in docker-compose.yaml

```yaml
services:
  web:
    volumes:
      - ./src:/app
      - ./src/config/firebase-service-account.json:/app/config/firebase-service-account.json:ro
```

### Option B: Copy into container manually

```bash
docker cp src/config/firebase-service-account.json sfs-services-dev-container:/app/config/firebase-service-account.json
```

## Step 7: Install Python Dependencies

## Step 7: Install Python Dependencies

Rebuild your Docker container to install `firebase-admin`:

```bash
docker-compose down
docker-compose build
docker-compose up
```

Or install manually in the container:

```bash
docker exec -it sfs-services-dev-container pip install firebase-admin==6.6.0
```

## Step 8: Test the Setup

## Step 8: Test the Setup

### 8.1 Check if Firebase Initializes

1. Open your browser's Developer Console (F12)
2. Navigate to your application
3. Look for these console messages:
   - "Firebase Messaging initialized successfully"
   - "Service Worker registered successfully"

### 8.2 Grant Notification Permission

1. When prompted, click "Allow" for notifications
2. Check console for: "Notification permission granted"
3. Check console for: "FCM token registered successfully with backend"

### 8.3 Test Push Notification

1. As a central admin user, make sure you're logged in
2. Have another user create a new issue in your organization
3. You should receive a push notification with:
   - Title: "New Issue: [Issue Title]"
   - Body: Priority and reporter information

## Step 9: Additional Configuration (Optional)

## Step 9: Additional Configuration (Optional)

### Move Service Worker to Root (Optional but Recommended)

Service workers work best when served from the root path. To do this:

1. Copy `firebase-messaging-sw.js` to your static root:
   ```bash
   cp src/static/js/firebase-messaging-sw.js src/static/firebase-messaging-sw.js
   ```

2. Update the service worker registration in `fcm-token-manager.js`:
   ```javascript
   const registration = await navigator.serviceWorker.register('/static/firebase-messaging-sw.js');
   ```

## Troubleshooting

### No Notification Permission Prompt

- Check if notifications are blocked in browser settings
- Try in an incognito window
- Make sure you're using HTTPS (or localhost for development)

### "Firebase not initialized" Error

- Verify Firebase config values are correct
- Check browser console for initialization errors
- Ensure Firebase CDN scripts are loading (check Network tab)

### Token Not Registered

- Check Django logs for registration errors
- Verify CSRF token is present on the page
- Check `/api/register-fcm-token/` endpoint is accessible

### No Push Notifications Received

- Verify the central admin has an `fcm_token` in the database
- Check Django logs for FCM sending errors
- Verify service account JSON file path is correct
- Make sure `firebase-admin` is installed
- Check Firebase Console > Cloud Messaging for error logs

### Service Worker Errors

- Service workers require HTTPS (except for localhost)
- Clear service worker cache: DevTools > Application > Service Workers > Unregister
- Hard refresh the page (Ctrl+Shift+R)

## Security Best Practices

1. **Never commit** `firebase-service-account.json` to Git
2. Add to `.gitignore`:
   ```
   src/config/firebase-service-account.json
   firebase-service-account.json
   ```
3. Use environment variables for all sensitive config
4. Rotate service account keys periodically
5. Limit Firebase project permissions to minimum required

## Testing Notifications Manually

You can test notifications using Firebase Console:

1. Go to Firebase Console > Cloud Messaging
2. Click "Send your first message"
3. Enter notification title and text
4. Click "Send test message"
5. Enter your FCM token (check browser console or database)
6. Click "Test"

## Architecture Summary

### Frontend Flow:
1. User visits application → Firebase SDK initializes
2. Request notification permission → User grants permission
3. Retrieve FCM token from Firebase
4. Send token to Django backend (`/api/register-fcm-token/`)
5. Backend stores token in `User.fcm_token` field

### Backend Flow:
1. Issue created → `post_save` signal triggered
2. Signal queries central admins in organization
3. For each admin with `fcm_token`, send notification via Firebase Admin SDK
4. Firebase delivers notification to user's device

### Notification Display:
- **Foreground (app open)**: Notification API shows notification
- **Background (app closed)**: Service worker shows notification
- **Click handler**: Opens issue detail page

## Files Modified/Created

### Created:
- `src/issue_management/utils/firebase_notifications.py` - FCM utility functions
- `src/static/js/firebase-messaging-sw.js` - Service worker for background notifications
- `src/static/js/fcm-token-manager.js` - Frontend FCM initialization and token management
- `docs/FIREBASE_PUSH_NOTIFICATIONS_SETUP.md` - This file

### Modified:
- `src/core/models.py` - Added `fcm_token` field to User model
- `src/issue_management/signals.py` - Added push notification on issue creation
- `src/core/views.py` - Added `RegisterFCMTokenView` API endpoint
- `src/core/urls.py` - Added URL for FCM token registration
- `src/templates/sidebar_base.html` - Added Firebase CDN scripts
- `src/requirements.txt` - Added `firebase-admin==6.6.0`
- `src/config/settings.py` - Added `FIREBASE_CREDENTIALS_PATH` configuration

## Next Steps

1. Set up Firebase project and get credentials (Steps 1-4)
2. Add Firebase config values to `.env` file (Step 5)
3. Add service account JSON file and configure path (Step 6)
4. Rebuild container and test (Steps 7-8)

**Important**: With the new implementation, you NO LONGER need to manually edit JavaScript files. All Firebase configuration is now managed through environment variables and served securely from the backend.

## Benefits of Environment-Based Configuration

1. **Security**: Sensitive config values are not hardcoded in JavaScript
2. **Flexibility**: Easy to change configuration without modifying code
3. **Environment Management**: Different configs for dev/staging/production
4. **No Code Changes**: Update Firebase credentials without touching source files
5. **Version Control**: JavaScript files can be committed without exposing credentials

## Support

For issues or questions:
- Check Firebase Console logs
- Review Django application logs
- Check browser console for JavaScript errors
- Verify all configuration values are correct
