// TrendVibe Essentials - Enhanced JavaScript

// Password strength validation
function validatePassword(password) {
    const requirements = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };
    
    const strength = Object.values(requirements).filter(Boolean).length;
    return { requirements, strength, isValid: strength === 5 };
}

function updatePasswordStrength(password, strengthIndicator, requirementsList) {
    const validation = validatePassword(password);
    
    // Update strength indicator
    const strengthTexts = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    const strengthColors = ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#28a745'];
    
    strengthIndicator.textContent = strengthTexts[validation.strength - 1] || 'Very Weak';
    strengthIndicator.style.color = strengthColors[validation.strength - 1] || '#dc3545';
    
    // Update requirements list
    const requirementElements = requirementsList.querySelectorAll('.requirement');
    requirementElements.forEach((el, index) => {
        const requirement = Object.values(validation.requirements)[index];
        el.classList.toggle('met', requirement);
        el.querySelector('i').className = requirement ? 'fas fa-check text-success' : 'fas fa-times text-danger';
    });
    
    return validation.isValid;
}

// Email validation
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Form validation enhancement
function enhanceFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const passwordField = form.querySelector('input[type="password"]');
            if (passwordField && passwordField.name === 'password') {
                const validation = validatePassword(passwordField.value);
                if (!validation.isValid) {
                    e.preventDefault();
                    alert('Password must meet all 5 security requirements: 8+ characters, uppercase, lowercase, number, and special character.');
                }
            }
        });
    });
}

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    // Initialize form validation
    enhanceFormValidation();
    
    // Initialize wishlist buttons
    initWishlistButtons();
    
    // Password strength indicator for registration form
    const passwordField = document.getElementById('password');
    const strengthIndicator = document.getElementById('password-strength');
    const progressBar = document.getElementById('password-progress');
    const requirementsList = document.getElementById('password-requirements');
    
    if (passwordField && strengthIndicator && requirementsList) {
        passwordField.addEventListener('input', function() {
            const password = this.value;
            const validation = validatePassword(password);
            
            // Update strength indicator
            const strengthTexts = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
            const strengthColors = ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#28a745'];
            
            strengthIndicator.textContent = strengthTexts[validation.strength - 1] || 'Very Weak';
            strengthIndicator.style.color = strengthColors[validation.strength - 1] || '#dc3545';
            
            // Update progress bar
            const progressPercent = (validation.strength / 5) * 100;
            progressBar.style.width = progressPercent + '%';
            progressBar.className = 'progress-bar';
            if (validation.strength === 5) progressBar.classList.add('bg-success');
            else if (validation.strength >= 3) progressBar.classList.add('bg-warning');
            else progressBar.classList.add('bg-danger');
            
            // Update requirements
            const requirementElements = requirementsList.querySelectorAll('.requirement');
            const requirements = Object.values(validation.requirements);
            requirementElements.forEach((el, index) => {
                const requirement = requirements[index];
                el.classList.toggle('text-success', requirement);
                el.classList.toggle('text-muted', !requirement);
                el.querySelector('i').className = requirement ? 'fas fa-check text-success me-1' : 'fas fa-times text-danger me-1';
            });
        });
    }
    // Smooth scroll for anchor links (exclude dropdowns, empty hashes, and Bootstrap toggles)
    const anchorLinks = document.querySelectorAll('a[href^="#"]:not([href="#"]):not([data-bs-toggle]):not(.dropdown-toggle)');
    anchorLinks.forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            // Only process if it's a valid anchor link and not a Bootstrap component
            if (href && href !== '#' && href.length > 1 && !this.hasAttribute('data-bs-toggle')) {
                e.preventDefault();
                const targetId = href.substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Add loading effect to product images
    const productImages = document.querySelectorAll('.product-card img');
    productImages.forEach(img => {
        img.style.opacity = '0';
        img.style.transition = 'opacity 0.3s ease';
        
        img.addEventListener('load', function() {
            this.style.opacity = '1';
        });
        
        // If image is already loaded
        if (img.complete) {
            img.style.opacity = '1';
        }
    });

    // Enhanced card hover effects
    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalText = submitButton.innerHTML;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
                submitButton.disabled = true;
                
                // Re-enable after form submission (in case of validation errors)
                setTimeout(() => {
                    submitButton.innerHTML = originalText;
                    submitButton.disabled = false;
                }, 3000);
            }
        });
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const alertInstance = new bootstrap.Alert(alert);
            alertInstance.close();
        }, 5000);
    });

    // Shopping cart count animation
    function animateCartCount() {
        const cartBadge = document.querySelector('.navbar-nav .badge');
        if (cartBadge) {
            cartBadge.style.transform = 'scale(1.2)';
            setTimeout(() => {
                cartBadge.style.transform = 'scale(1)';
            }, 200);
        }
    }

    // Search functionality enhancement
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const searchIcon = document.querySelector('.input-group-text .fas');
            
            if (this.value.length > 0) {
                searchIcon.className = 'fas fa-times text-muted';
                searchIcon.style.cursor = 'pointer';
                searchIcon.onclick = () => {
                    searchInput.value = '';
                    searchIcon.className = 'fas fa-search text-muted';
                    searchIcon.style.cursor = 'default';
                    searchIcon.onclick = null;
                };
            } else {
                searchIcon.className = 'fas fa-search text-muted';
                searchIcon.style.cursor = 'default';
                searchIcon.onclick = null;
            }
        });
    }

    // Quantity selector enhancement
    const quantitySelects = document.querySelectorAll('select[name="quantity"]');
    quantitySelects.forEach(select => {
        select.addEventListener('change', function() {
            const quantity = parseInt(this.value);
            const priceElement = document.querySelector('.product-price');
            
            if (priceElement && window.productPrice) {
                const total = quantity * window.productPrice;
                // You can add total display logic here if needed
            }
        });
    });

    // Back to top button
    const backToTopBtn = document.createElement('button');
    backToTopBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    backToTopBtn.className = 'btn btn-primary position-fixed';
    backToTopBtn.style.cssText = `
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        display: none;
        box-shadow: 0 4px 15px rgba(9, 12, 155, 0.3);
    `;
    
    document.body.appendChild(backToTopBtn);
    
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            backToTopBtn.style.display = 'block';
        } else {
            backToTopBtn.style.display = 'none';
        }
    });
    
    backToTopBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // Local storage cart management
    function updateCartDisplay() {
        const cartCount = document.querySelector('.navbar-nav .badge');
        const cart = JSON.parse(localStorage.getItem('cart') || '{}');
        const totalItems = Object.values(cart).reduce((sum, qty) => sum + qty, 0);
        
        if (cartCount && totalItems > 0) {
            cartCount.textContent = totalItems;
            cartCount.style.display = 'inline';
        } else if (cartCount) {
            cartCount.style.display = 'none';
        }
    }

    // Initialize cart display
    updateCartDisplay();

    // Add to cart button enhancement
    const addToCartForms = document.querySelectorAll('form[action*="add_to_cart"]');
    addToCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            animateCartCount();
            
            // Store in local storage as backup
            const productId = this.action.split('/').pop();
            const quantity = parseInt(this.querySelector('select[name="quantity"]').value || 1);
            
            const cart = JSON.parse(localStorage.getItem('cart') || '{}');
            cart[productId] = (cart[productId] || 0) + quantity;
            localStorage.setItem('cart', JSON.stringify(cart));
            
            updateCartDisplay();
        });
    });
});

// Wishlist functionality
function updateWishlistCount(count) {
    const badge = document.getElementById('wishlist-count');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline' : 'none';
    }
}

function initWishlistButtons() {
    document.querySelectorAll('.wishlist-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const productId = this.dataset.productId;
            const icon = this.querySelector('i');
            const isInWishlist = icon.classList.contains('text-danger');
            const url = isInWishlist
                ? `/remove_from_wishlist/${productId}`
                : `/add_to_wishlist/${productId}`;

            const csrfToken = document.querySelector('meta[name="csrf-token"]') 
                ? document.querySelector('meta[name="csrf-token"]').content
                : '';

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (isInWishlist) {
                        icon.classList.remove('text-danger');
                        this.title = 'Add to wishlist';
                    } else {
                        icon.classList.add('text-danger');
                        this.title = 'Remove from wishlist';
                    }
                    updateWishlistCount(data.wishlist_count);
                    showNotification(data.message, 'success');
                } else {
                    showNotification(data.message, 'warning');
                }
            })
            .catch(() => {
                showNotification('Could not update wishlist. Please try again.', 'danger');
            });
        });
    });
}

// Utility functions
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        const alert = new bootstrap.Alert(alertDiv);
        alert.close();
    }, 5000);
}

function formatPrice(price) {
    return `₹${price.toLocaleString('en-IN')}`;
}

// Export for use in other scripts
window.ZenCart = {
    showNotification,
    formatPrice,
    updateCartDisplay: function() {
        // Call the internal updateCartDisplay function if available
        if (typeof updateCartDisplay === 'function') {
            updateCartDisplay();
        }
    }
};