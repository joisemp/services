/* home.js — landing page interactions
   - Navbar: transparent → solid on scroll
   - Scroll-reveal: elements with class .reveal animate in when visible
*/

(function () {
    'use strict';

    // ── Navbar scroll state ───────────────────────────────────────────────────
    var header = document.getElementById('home-header');

    function updateNav() {
        if (!header) return;
        if (window.scrollY > 48) {
            header.classList.add('nav-scrolled');
        } else {
            header.classList.remove('nav-scrolled');
        }
    }

    window.addEventListener('scroll', updateNav, { passive: true });
    updateNav(); // run once on load in case page is already scrolled

    // ── Scroll-reveal ─────────────────────────────────────────────────────────
    var revealEls = [];

    function collectRevealTargets() {
        // Add .reveal to key interior elements after DOM is ready
        var selectors = [
            '#features .feature-card',
            '#how-it-works .step-card',
            '#who-its-for .role-card',
            '#faq .accordion-item'
        ];

        selectors.forEach(function (sel) {
            document.querySelectorAll(sel).forEach(function (el) {
                el.classList.add('reveal');
                revealEls.push(el);
            });
        });
    }

    function checkReveal() {
        var windowBottom = window.scrollY + window.innerHeight;
        revealEls.forEach(function (el) {
            if (el.classList.contains('reveal-visible')) return;
            var elTop = el.getBoundingClientRect().top + window.scrollY;
            if (windowBottom > elTop + 60) {
                el.classList.add('reveal-visible');
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        collectRevealTargets();
        checkReveal(); // catch anything already in viewport
        window.addEventListener('scroll', checkReveal, { passive: true });
    });

})();
