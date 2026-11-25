/**
 * Dismiss the branded splash after standalone launch.
 */
(function pwaSplash() {
    const root = document.documentElement;
    const splash = document.getElementById('pwa-splash');
    if (!splash || !root.classList.contains('pwa-standalone')) {
        return;
    }

    if (root.classList.contains('pwa-splash-done')) {
        return;
    }

    const SESSION_KEY = 'services-pwa-splash-shown';
    const MIN_VISIBLE_MS = 1100;
    const FADE_MS = 450;
    const shownAt = Date.now();

    splash.setAttribute('aria-hidden', 'false');
    sessionStorage.setItem(SESSION_KEY, '1');

    function hideSplash() {
        splash.classList.add('is-leaving');
        window.setTimeout(() => {
            root.classList.add('pwa-splash-done');
            splash.setAttribute('aria-hidden', 'true');
            splash.classList.remove('is-leaving');
        }, FADE_MS);
    }

    function finish() {
        const wait = Math.max(0, MIN_VISIBLE_MS - (Date.now() - shownAt));
        window.setTimeout(hideSplash, wait);
    }

    if (document.readyState === 'complete') {
        finish();
    } else {
        window.addEventListener('load', finish, { once: true });
    }
})();
