/**
 * Recipe Editor - Client-side JavaScript
 */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    // DO NOT auto-dismiss alerts - let them stay on screen
    // User requested all error, warning, and informational messages stay visible
    // Users can manually dismiss them using the X button if present
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
});

/**
 * Form validation helper
 */
function validateRecipeForm() {
    const form = document.getElementById('recipeForm');
    if (!form) return true;

    const name = document.getElementById('name').value.trim();
    if (!name) {
        alert('Recipe name is required.');
        return false;
    }

    // Check if at least one ingredient has a description
    const ingredientDescriptions = form.querySelectorAll('[name^="ingredient_description_"]');
    let hasIngredient = false;
    ingredientDescriptions.forEach(input => {
        if (input.value.trim()) {
            hasIngredient = true;
        }
    });

    if (!hasIngredient) {
        alert('At least one ingredient with a description is required.');
        return false;
    }

    // Validate amounts if provided
    const ingredientAmounts = form.querySelectorAll('[name^="ingredient_amount_"]');
    for (let input of ingredientAmounts) {
        const amount = input.value.trim();
        if (amount && !isValidAmount(amount)) {
            alert(`Invalid amount: "${amount}". Please use numbers or fractions (e.g., 1/2, 2.5).`);
            input.focus();
            return false;
        }
    }

    return true;
}

/**
 * Validate ingredient amount format
 */
function isValidAmount(amount) {
    if (!amount) return true;
    
    // Simple number (integer or decimal)
    if (/^\d+\.?\d*$/.test(amount)) {
        const value = parseFloat(amount);
        return value >= 0 && value <= 1000;
    }
    
    // Fraction (e.g., 1/2)
    if (/^\d+\/\d+$/.test(amount)) {
        const parts = amount.split('/');
        const numerator = parseInt(parts[0]);
        const denominator = parseInt(parts[1]);
        if (denominator === 0) return false;
        const value = numerator / denominator;
        return value >= 0 && value <= 1000;
    }
    
    // Mixed number (e.g., 1 1/2)
    if (/^\d+\s+\d+\/\d+$/.test(amount)) {
        const parts = amount.split(/\s+/);
        const whole = parseInt(parts[0]);
        const fracParts = parts[1].split('/');
        const numerator = parseInt(fracParts[0]);
        const denominator = parseInt(fracParts[1]);
        if (denominator === 0) return false;
        const value = whole + (numerator / denominator);
        return value >= 0 && value <= 1000;
    }
    
    return false;
}

/**
 * Email validation
 */
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Add loading state to button
 */
function setButtonLoading(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
}

/**
 * Show confirmation modal
 */
function showConfirmModal(title, message, onConfirm) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('confirmModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'confirmModal';
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="confirmModalTitle"></h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="confirmModalBody"></div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="confirmModalButton">Confirm</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    document.getElementById('confirmModalTitle').textContent = title;
    document.getElementById('confirmModalBody').textContent = message;
    
    const confirmButton = document.getElementById('confirmModalButton');
    confirmButton.onclick = function() {
        const bsModal = bootstrap.Modal.getInstance(modal);
        bsModal.hide();
        onConfirm();
    };

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Format date string
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
}

/**
 * Smooth scroll to element
 */
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('Copied to clipboard!', 'success');
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    // Set autohide to false so toasts stay visible until manually dismissed
    const bsToast = new bootstrap.Toast(toast, { autohide: false });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

/**
 * Show detailed email sent notification
 */
function showEmailSentNotification(recipientName, recipientEmail, message, recipeName) {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-success border-0';
    toast.setAttribute('role', 'alert');
    toast.style.minWidth = '350px';
    
    const displayName = recipientName || 'Recipient';
    const displayMessage = message ? `"${message.length > 50 ? message.substring(0, 50) + '...' : message}"` : 'No custom message';
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <div class="d-flex align-items-center mb-2">
                    <i class="bi bi-envelope-check-fill me-2"></i>
                    <strong>Email Sent Successfully!</strong>
                </div>
                <div class="small">
                    <div><strong>To:</strong> ${displayName} (${recipientEmail})</div>
                    <div><strong>Recipe:</strong> ${recipeName}</div>
                    <div><strong>Message:</strong> ${displayMessage}</div>
                </div>
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { autohide: false });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

/**
 * Show email error notification
 */
function showEmailErrorNotification(errorMessage, recipientEmail) {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-danger border-0';
    toast.setAttribute('role', 'alert');
    toast.style.minWidth = '350px';
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <div class="d-flex align-items-center mb-2">
                    <i class="bi bi-envelope-x-fill me-2"></i>
                    <strong>Email Failed to Send</strong>
                </div>
                <div class="small">
                    <div><strong>To:</strong> ${recipientEmail}</div>
                    <div><strong>Error:</strong> ${errorMessage}</div>
                </div>
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { autohide: false });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

/**
 * Create toast container if it doesn't exist
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

/**
 * Debounce function for search/filter inputs
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Local storage helpers
 */
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error('Error saving to localStorage:', e);
        }
    },
    
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Error reading from localStorage:', e);
            return defaultValue;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.error('Error removing from localStorage:', e);
        }
    }
};

// Export functions for use in templates
window.RecipeEditor = {
    validateRecipeForm,
    isValidAmount,
    isValidEmail,
    setButtonLoading,
    showConfirmModal,
    formatDate,
    scrollToElement,
    copyToClipboard,
    showToast,
    showEmailSentNotification,
    showEmailErrorNotification,
    debounce,
    Storage
};

