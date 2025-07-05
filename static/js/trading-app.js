// Algolab Trading Platform - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle functionality
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            mainContent.classList.toggle('active');
            sidebarOverlay.classList.toggle('active');
        });
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            sidebar.classList.remove('active');
            mainContent.classList.remove('active');
            sidebarOverlay.classList.remove('active');
        });
    }
    
    // Set active menu item based on current page
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('.sidebar-menu a');
    
    menuItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href === currentPath || currentPath.includes(href) && href !== '/') {
            item.classList.add('active');
            
            // If this is a submenu item, also activate its parent
            const parentLi = item.closest('li');
            if (parentLi && parentLi.closest('.submenu')) {
                const parentSubmenu = parentLi.closest('.submenu');
                const parentMenuItem = parentSubmenu.closest('.has-submenu');
                if (parentMenuItem) {
                    parentMenuItem.classList.add('active');
                }
            }
        }
    });
    
    // Toggle submenu on click
    const submenuItems = document.querySelectorAll('.has-submenu > a');
    submenuItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const parent = this.parentElement;
            parent.classList.toggle('active');
        });
    });
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Format numbers with commas for thousands
    const formatNumberElements = document.querySelectorAll('.format-number');
    formatNumberElements.forEach(element => {
        const value = parseFloat(element.textContent);
        if (!isNaN(value)) {
            element.textContent = value.toLocaleString('tr-TR');
        }
    });
    
    // Add animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.classList.add('fade-in');
    });
});

// Function to refresh data without page reload
function refreshData(endpoint, targetElement) {
    fetch(endpoint)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById(targetElement).innerHTML = data.html;
            }
        })
        .catch(error => console.error('Error refreshing data:', error));
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('tr-TR', {
        style: 'currency',
        currency: 'TRY'
    }).format(amount);
}

// Format percentage
function formatPercentage(value) {
    return new Intl.NumberFormat('tr-TR', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

// Toggle password visibility
function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}
