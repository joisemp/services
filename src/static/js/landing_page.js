document.addEventListener('DOMContentLoaded', function() {
    // Basic functionality without animations
    console.log('Landing page loaded');
});

// Minimal CSS for basic functionality
const style = document.createElement('style');
style.textContent = `
    .btn {
        cursor: pointer;
    }
    
    .dropdown-menu {
        animation: none !important;
    }
`;
document.head.appendChild(style);
