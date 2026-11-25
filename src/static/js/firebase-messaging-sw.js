/**
 * Combined PWA + Firebase Cloud Messaging service worker.
 * - Installable app shell with network-first navigation
 * - Offline fallback at /offline/
 * - Background push notifications (FCM)
 */

importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js');

const CACHE_VERSION = 'services-pwa-v1';
const OFFLINE_URL = '/offline/';
const PRECACHE_URLS = [OFFLINE_URL];

let messaging = null;
let notificationIcon = '/static/images/notification-icon.png';
let notificationBadge = '/static/images/notification-badge.png';

const DEBUG_MODE = false;

function debugLog(...args) {
    if (DEBUG_MODE) {
        console.log(...args);
    }
}

self.addEventListener('install', (event) => {
    event.waitUntil(
        (async () => {
            const cache = await caches.open(CACHE_VERSION);
            await cache.addAll(PRECACHE_URLS);
            await self.skipWaiting();
        })()
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        (async () => {
            const keys = await caches.keys();
            await Promise.all(
                keys
                    .filter((key) => key !== CACHE_VERSION)
                    .map((key) => caches.delete(key))
            );
            await self.clients.claim();
        })()
    );
});

self.addEventListener('fetch', (event) => {
    const { request } = event;

    if (request.method !== 'GET') {
        return;
    }

    const url = new URL(request.url);

    // Same-origin document navigations: network-first, offline fallback
    const isNavigation =
        request.mode === 'navigate' ||
        (request.headers.get('accept') || '').includes('text/html');

    if (isNavigation && url.origin === self.location.origin) {
        event.respondWith(
            (async () => {
                try {
                    const networkResponse = await fetch(request);
                    return networkResponse;
                } catch (error) {
                    const cache = await caches.open(CACHE_VERSION);
                    const offline = await cache.match(OFFLINE_URL);
                    if (offline) {
                        return offline;
                    }
                    return new Response('You are offline.', {
                        status: 503,
                        headers: { 'Content-Type': 'text/plain' },
                    });
                }
            })()
        );
    }
});

self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'FIREBASE_CONFIG') {
        const firebaseConfig = event.data.config;

        if (event.data.notificationIcon) {
            notificationIcon = event.data.notificationIcon;
        }
        if (event.data.notificationBadge) {
            notificationBadge = event.data.notificationBadge;
        }

        if (!firebase.apps.length) {
            firebase.initializeApp(firebaseConfig);
            messaging = firebase.messaging();

            messaging.onBackgroundMessage((payload) => {
                debugLog('Received background message:', payload);

                const notificationTitle = payload.notification?.title || 'Services';
                const notificationOptions = {
                    body: payload.notification?.body || '',
                    icon: notificationIcon,
                    badge: notificationBadge,
                    data: payload.data || {},
                };

                return self.registration.showNotification(
                    notificationTitle,
                    notificationOptions
                );
            });
        }
    }
});

self.addEventListener('notificationclick', (event) => {
    debugLog('Notification clicked:', event);
    event.notification.close();

    const issueSlug = event.notification.data?.ticket_slug;

    if (issueSlug) {
        event.waitUntil(
            clients.openWindow(`/tickets/central-admin/${issueSlug}/`)
        );
    } else {
        event.waitUntil(clients.openWindow('/'));
    }
});
