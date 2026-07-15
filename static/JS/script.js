// Listen for the user scrolling
window.addEventListener('scroll', function() {
    const navbar = document.getElementById('homeNavbar');
    // If scrolled down more than 50 pixels
    if (window.scrollY > 50) {
        navbar.classList.add('navbar-scrolled');
        navbar.classList.remove('navbar-transparent');
    } else {
        // If back at the top
        navbar.classList.add('navbar-transparent');
        navbar.classList.remove('navbar-scrolled');
    }
});

document.querySelectorAll('.btn-minus').forEach(button => {
    // Using .onclick ensures only one event fires, preventing the "+2" bug
    button.onclick = function(e) {
        e.preventDefault(); // Prevents the button from doing anything else
        const targetId = this.getAttribute('data-target');
        const input = document.getElementById(targetId);
        const min = parseInt(input.getAttribute('min'));
        let val = parseInt(input.value);
        if (val > min) {
            input.value = val - 1;
        }
    };
});

document.querySelectorAll('.btn-plus').forEach(button => {
    button.onclick = function(e) {
        e.preventDefault(); 
        const targetId = this.getAttribute('data-target');
        const input = document.getElementById(targetId);
        const max = parseInt(input.getAttribute('max'));
        let val = parseInt(input.value);
        if (val < max) {
            input.value = val + 1;
        }
    };
});

document.addEventListener("DOMContentLoaded", function() {
    // Check if there are query parameters in the URL (meaning a filter was applied)
    if (window.location.search) {
        const resultsSection = document.getElementById('quest-results');
        if (resultsSection) {
            // A tiny delay ensures the browser has fully built the page layout before calculating the scroll distance
            setTimeout(() => {
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 500);
        }
    }
});