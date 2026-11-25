/**
 * Register the root PWA service worker on every page shell.
 * FCM reuses the same registration when initializing push.
 */
(function registerPwaServiceWorker() {
    if (!('serviceWorker' in navigator)) {
        return;
    }

    const SW_URL = '/firebase-messaging-sw.js';

    window.addEventListener('load', () => {
        navigator.serviceWorker.register(SW_URL, { scope: '/' }).catch((error) => {
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                console.warn('PWA service worker registration failed:', error);
            }
        });
    });
})();
