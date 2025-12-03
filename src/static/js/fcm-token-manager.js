/**
 * Firebase Cloud Messaging (FCM) Token Management
 * Handles FCM initialization, token retrieval, and registration
 */

// Firebase configuration will be loaded from backend
let firebaseConfig = null;
let vapidKey = null;
let messaging = null;

// Debug mode - set to false in production
const DEBUG_MODE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

// Console log wrapper for debug mode
function debugLog(...args) {
    if (DEBUG_MODE) {
        console.log(...args);
    }
}

function debugError(...args) {
    console.error(...args);
}

function debugWarn(...args) {
    if (DEBUG_MODE) {
        console.warn(...args);
    }
}

/**
 * Fetch Firebase configuration from backend
 */
async function fetchFirebaseConfig() {
    try {
        const response = await fetch('/core/api/firebase-config/');
        
        if (!response.ok) {
            throw new Error('Failed to fetch Firebase configuration');
        }
        
        const config = await response.json();
        
        debugLog('Fetched Firebase config:', config);
        
        // Validate that we have all required fields
        if (!config.apiKey || !config.projectId || !config.appId) {
            debugError('Firebase config is incomplete:', config);
            throw new Error('Firebase configuration is missing required fields. Please check your .env file.');
        }
        
        // Extract VAPID key and prepare Firebase config
        vapidKey = config.vapidKey;
        firebaseConfig = {
            apiKey: config.apiKey,
            authDomain: config.authDomain,
            projectId: config.projectId,
            storageBucket: config.storageBucket,
            messagingSenderId: config.messagingSenderId,
            appId: config.appId
        };
        
        debugLog('Firebase config loaded successfully');
        return true;
    } catch (error) {
        debugError('Error fetching Firebase configuration:', error);
        return false;
    }
}

function initializeFirebase() {
    try {
        if (!firebaseConfig) {
            debugError('Firebase config not loaded');
            return false;
        }
        
        if (!firebase.apps.length) {
            firebase.initializeApp(firebaseConfig);
        }
        
        // Check if messaging is supported
        if (firebase.messaging.isSupported()) {
            messaging = firebase.messaging();
            debugLog('Firebase Messaging initialized successfully');
            return true;
        } else {
            debugWarn('Firebase Messaging is not supported in this browser');
            return false;
        }
    } catch (error) {
        debugError('Error initializing Firebase:', error);
        return false;
    }
}

/**
 * Request notification permission from the user
 */
async function requestNotificationPermission() {
    try {
        const permission = await Notification.requestPermission();
        
        if (permission === 'granted') {
            debugLog('Notification permission granted');
            return true;
        } else if (permission === 'denied') {
            debugWarn('Notification permission denied');
            return false;
        } else {
            debugWarn('Notification permission dismissed');
            return false;
        }
    } catch (error) {
        debugError('Error requesting notification permission:', error);
        return false;
    }
}

/**
 * Get FCM token and register it with the backend
 */
async function getAndRegisterFCMToken() {
    debugLog('getAndRegisterFCMToken: Starting...');
    
    if (!messaging) {
        debugWarn('Firebase Messaging not initialized');
        return null;
    }
    debugLog('getAndRegisterFCMToken: Messaging initialized');
    
    if (!vapidKey) {
        debugError('VAPID key not loaded');
        return null;
    }
    debugLog('getAndRegisterFCMToken: VAPID key loaded');
    
    try {
        debugLog('getAndRegisterFCMToken: Getting service worker registration...');
        // Get the service worker registration from root scope
        const registration = await navigator.serviceWorker.getRegistration('/');
        
        if (!registration) {
            debugError('Service worker registration not found');
            return null;
        }
        
        debugLog('getAndRegisterFCMToken: Got registration, requesting token from Firebase...');
        
        // Get registration token with custom service worker
        const currentToken = await messaging.getToken({
            vapidKey: vapidKey,
            serviceWorkerRegistration: registration
        });
        
        if (currentToken) {
            debugLog('FCM Token retrieved:', currentToken);
            
            // Send token to backend
            debugLog('getAndRegisterFCMToken: Sending token to backend...');
            await registerTokenWithBackend(currentToken);
            
            return currentToken;
        } else {
            debugWarn('No FCM token available. Request permission to generate one.');
            return null;
        }
    } catch (error) {
        debugError('Error getting FCM token:', error);
        debugError('Error details:', error.message, error.stack);
        return null;
    }
}

/**
 * Register FCM token with Django backend
 */
async function registerTokenWithBackend(token) {
    try {
        // Get CSRF token from meta tag or cookie
        let csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        
        if (!csrfToken) {
            // Fallback to cookie
            csrfToken = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1];
        }
        
        if (!csrfToken) {
            debugError('CSRF token not found');
            return false;
        }
        
        const response = await fetch('/core/api/register-fcm-token/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                fcm_token: token
            })
        });
        
        if (response.ok) {
            debugLog('FCM token registered successfully with backend');
            return true;
        } else {
            const errorText = await response.text();
            debugError('Failed to register FCM token with backend:', errorText);
            return false;
        }
    } catch (error) {
        debugError('Error registering FCM token with backend:', error);
        return false;
    }
}

/**
 * Handle incoming messages when the app is in foreground
 */
function setupForegroundMessageHandler() {
    if (!messaging) {
        return;
    }
    
    messaging.onMessage((payload) => {
        debugLog('Message received in foreground:', payload);
        
        const notificationTitle = payload.notification.title;
        const notificationOptions = {
            body: payload.notification.body,
            icon: '/static/images/notification-icon.png',
            badge: '/static/images/notification-badge.png',
            data: payload.data
        };
        
        // Show notification using Notification API
        if (Notification.permission === 'granted') {
            const notification = new Notification(notificationTitle, notificationOptions);
            
            // Handle notification click
            notification.onclick = function(event) {
                event.preventDefault();
                const issueSlug = payload.data?.issue_slug;
                
                if (issueSlug) {
                    window.open(`/issues/central-admin/${issueSlug}/`, '_blank');
                }
                
                notification.close();
            };
        }
    });
}

/**
 * Register service worker for background notifications
 */
async function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        try {
            // Register service worker from root path for proper scope
            const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
            debugLog('Service Worker registered successfully:', registration);
            
            return registration;
        } catch (error) {
            debugError('Service Worker registration failed:', error);
            return null;
        }
    } else {
        debugWarn('Service Worker is not supported in this browser');
        return null;
    }
}

/**
 * Initialize FCM - Main entry point
 */
async function initializeFCM() {
    // Check if browser supports notifications
    if (!('Notification' in window)) {
        debugWarn('This browser does not support notifications');
        return;
    }
    
    // Fetch Firebase config from backend
    const configLoaded = await fetchFirebaseConfig();
    if (!configLoaded) {
        debugError('Failed to load Firebase configuration');
        return;
    }
    
    // Initialize Firebase
    if (!initializeFirebase()) {
        return;
    }
    
    try {
        // Register service worker
        debugLog('Registering service worker...');
        const registration = await registerServiceWorker();
        if (!registration) {
            debugError('Service worker registration failed');
            return;
        }
        
        debugLog('Service worker registered, waiting for it to be active...');
        
        // Wait a bit for service worker to activate if needed
        if (!registration.active) {
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        // Send Firebase config to service worker
        const activeWorker = registration.active;
        if (activeWorker) {
            debugLog('Sending Firebase config to service worker');
            activeWorker.postMessage({
                type: 'FIREBASE_CONFIG',
                config: firebaseConfig
            });
        }
        
        // Request permission
        debugLog('Requesting notification permission...');
        const permissionGranted = await requestNotificationPermission();
        
        if (permissionGranted) {
            debugLog('Permission granted, getting FCM token...');
            // Get and register FCM token
            await getAndRegisterFCMToken();
            
            // Setup foreground message handler
            setupForegroundMessageHandler();
            
            debugLog('FCM initialization complete!');
        } else {
            debugWarn('Notification permission not granted');
        }
    } catch (error) {
        debugError('Error during FCM initialization:', error);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', async () => {
        await initializeFCM();
    });
} else {
    // DOM already loaded
    (async () => {
        await initializeFCM();
    })();
}
