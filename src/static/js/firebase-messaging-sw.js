/**
 * Firebase Cloud Messaging (FCM) Service Worker Configuration
 * This file handles background push notifications
 */

// Import Firebase scripts
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js');

// Firebase config will be set dynamically via message from main thread
let messaging = null;

// Listen for message from main thread with Firebase config
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'FIREBASE_CONFIG') {
        const firebaseConfig = event.data.config;
        
        if (!firebase.apps.length) {
            firebase.initializeApp(firebaseConfig);
            messaging = firebase.messaging();
            
            // Set up background message handler
            messaging.onBackgroundMessage((payload) => {
                console.log('Received background message:', payload);
                
                const notificationTitle = payload.notification.title;
                const notificationOptions = {
                    body: payload.notification.body,
                    icon: '/static/images/notification-icon.png',
                    badge: '/static/images/notification-badge.png',
                    data: payload.data
                };
                
                return self.registration.showNotification(notificationTitle, notificationOptions);
            });
        }
    }
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event);
    event.notification.close();
    
    // Get the issue slug from notification data
    const issueSlug = event.notification.data?.issue_slug;
    
    if (issueSlug) {
        // Navigate to the issue detail page
        event.waitUntil(
            clients.openWindow(`/issues/central-admin/${issueSlug}/`)
        );
    }
});
