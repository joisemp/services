/**
 * YouTube-style Loading Progress Bar
 * Automatically shows on page load, HTMX requests, and form submissions
 */

class LoadingProgress {
    constructor() {
        this.progressBar = null;
        this.currentProgress = 0;
        this.targetProgress = 0;
        this.isActive = false;
        this.animationFrame = null;
        this.autoIncrementInterval = null;
        this.init();
    }

    init() {
        // Wait for body to be available
        if (!document.body) {
            document.addEventListener('DOMContentLoaded', () => this.init());
            return;
        }

        // Create progress bar element
        this.progressBar = document.createElement('div');
        this.progressBar.id = 'loading-progress-bar';
        document.body.prepend(this.progressBar);

        // Set up event listeners
        this.setupEventListeners();

        // Show briefly on load to test
        console.log('Loading progress bar initialized');
    }

    setupEventListeners() {
        // Page load progress
        if (document.readyState === 'loading') {
            this.start();
            window.addEventListener('DOMContentLoaded', () => {
                this.setProgress(70);
            });
            window.addEventListener('load', () => {
                this.complete();
            });
        }

        // HTMX events
        document.body.addEventListener('htmx:beforeRequest', () => {
            this.start();
        });

        document.body.addEventListener('htmx:afterRequest', () => {
            this.complete();
        });

        document.body.addEventListener('htmx:responseError', () => {
            this.complete();
        });

        // Form submission events
        document.body.addEventListener('htmx:beforeSend', () => {
            this.start();
        });

        // Regular form submissions (non-HTMX)
        document.body.addEventListener('submit', (e) => {
            // Check if it's not an HTMX form
            if (!e.target.hasAttribute('hx-post') && !e.target.hasAttribute('hx-get')) {
                this.start();
            }
        });

        // Navigation events
        window.addEventListener('beforeunload', () => {
            this.start();
        });

        // Handle back/forward navigation
        window.addEventListener('pageshow', (event) => {
            if (event.persisted) {
                this.complete();
            }
        });

        // Show progress on link clicks (except hash links and external)
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && link.href && !link.hasAttribute('hx-get') && !link.hasAttribute('hx-post')) {
                const url = new URL(link.href, window.location.href);
                // Only for same-origin navigation links (not hash or external)
                if (url.origin === window.location.origin && !url.hash) {
                    this.start();
                }
            }
        });
    }

    start() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.currentProgress = 0;
        this.targetProgress = 0;
        this.progressBar.classList.remove('complete');
        this.progressBar.classList.add('active');
        this.progressBar.style.width = '0%';
        
        // Start auto-increment
        this.autoIncrement();
    }

    autoIncrement() {
        // Clear existing interval
        if (this.autoIncrementInterval) {
            clearInterval(this.autoIncrementInterval);
        }

        // Auto-increment progress slowly
        this.autoIncrementInterval = setInterval(() => {
            if (this.targetProgress < 90) {
                // Slow down as we approach 90%
                const increment = (90 - this.targetProgress) * 0.05;
                this.setProgress(this.targetProgress + increment);
            }
        }, 200);
    }

    setProgress(progress) {
        this.targetProgress = Math.min(progress, 100);
        this.animate();
    }

    animate() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }

        const step = () => {
            if (Math.abs(this.currentProgress - this.targetProgress) < 0.1) {
                this.currentProgress = this.targetProgress;
                this.progressBar.style.width = `${this.currentProgress}%`;
                return;
            }

            this.currentProgress += (this.targetProgress - this.currentProgress) * 0.1;
            this.progressBar.style.width = `${this.currentProgress}%`;
            this.animationFrame = requestAnimationFrame(step);
        };

        this.animationFrame = requestAnimationFrame(step);
    }

    complete() {
        if (!this.isActive) return;

        // Clear auto-increment
        if (this.autoIncrementInterval) {
            clearInterval(this.autoIncrementInterval);
            this.autoIncrementInterval = null;
        }

        // Jump to 100%
        this.setProgress(100);

        // Wait a bit then hide
        setTimeout(() => {
            this.progressBar.classList.add('complete');
            this.progressBar.classList.remove('active');
            this.isActive = false;
            
            // Reset after animation
            setTimeout(() => {
                if (!this.isActive) {
                    this.progressBar.style.width = '0%';
                    this.currentProgress = 0;
                    this.targetProgress = 0;
                }
            }, 500);
        }, 300);
    }

    // Public method to manually trigger progress
    show() {
        this.start();
    }

    // Public method to manually complete progress
    hide() {
        this.complete();
    }

    // Test method to see if it works
    test() {
        this.start();
        setTimeout(() => {
            this.setProgress(50);
        }, 500);
        setTimeout(() => {
            this.complete();
        }, 2000);
    }
}

// Initialize immediately
const loadingProgress = new LoadingProgress();

// Expose to global scope for manual control if needed
window.loadingProgress = loadingProgress;
