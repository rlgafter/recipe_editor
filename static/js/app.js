/**
 * Source input popup for recipe uploads
 */
function showSourceInputPopup(recipeData, callback) {
    // Create popup HTML
    const popupHtml = `
        <div id="sourceInputModal" class="modal fade" tabindex="-1" role="dialog">
            <div class="modal-dialog modal-lg" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Recipe Source Information</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i>
                            This recipe appears to be adapted from another source. Please provide where you found it.
                        </div>
                        
                        <form id="sourceInputForm">
                            <div class="mb-3">
                                <label for="sourceName" class="form-label">Source Name *</label>
                                <input type="text" class="form-control" id="sourceName" 
                                       placeholder="e.g., NYT Cooking, Food52, Bon Appétit" required>
                                <div class="form-text">The website or publication where you found this recipe</div>
                            </div>
                            
                            <div class="mb-3">
                                <label for="sourceUrl" class="form-label">URL</label>
                                <input type="url" class="form-control" id="sourceUrl" 
                                       placeholder="https://cooking.nytimes.com/recipes/...">
                                <div class="form-text">The direct link to the recipe (if publicly accessible)</div>
                            </div>
                            
                            <div class="mb-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="privateSource">
                                    <label class="form-check-label" for="privateSource">
                                        This is a private source (not publicly accessible)
                                    </label>
                                </div>
                                <div class="form-text">Check this if the recipe is from a private source or you don't have a public URL</div>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Original Source Information</label>
                                <div class="card">
                                    <div class="card-body">
                                        <p class="mb-1"><strong>Name:</strong> ${recipeData.source?.original_source?.name || 'Not specified'}</p>
                                        <p class="mb-1"><strong>Author:</strong> ${recipeData.source?.original_source?.author || 'Not specified'}</p>
                                        <p class="mb-0"><strong>Publisher:</strong> ${recipeData.source?.original_source?.issue || 'Not specified'}</p>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="saveSourceBtn">Save Recipe</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('sourceInputModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', popupHtml);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('sourceInputModal'));
    modal.show();
    
    // Handle form submission
    document.getElementById('saveSourceBtn').addEventListener('click', function() {
        const form = document.getElementById('sourceInputForm');
        const formData = new FormData(form);
        
        const sourceData = {
            name: document.getElementById('sourceName').value.trim(),
            url: document.getElementById('sourceUrl').value.trim(),
            isPrivate: document.getElementById('privateSource').checked
        };
        
        // Validate required fields
        if (!sourceData.name) {
            alert('Please enter a source name');
            return;
        }
        
        // Validate URL if provided
        if (sourceData.url && !isValidUrl(sourceData.url)) {
            alert('Please enter a valid URL');
            return;
        }
        
        // Update recipe data with source information
        if (!recipeData.source) {
            recipeData.source = {};
        }
        
        recipeData.source.name = sourceData.name;
        recipeData.source.url = sourceData.url;
        
        // Hide modal
        modal.hide();
        
        // Call callback with updated recipe data
        callback(recipeData);
    });
    
    // Handle modal close
    document.getElementById('sourceInputModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

/**
 * Validate URL format
 */
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

/**
 * Check if recipe needs source input popup
 */
function needsSourceInput(recipeData) {
    // Check if this is an adapted recipe with missing source info
    const source = recipeData.source || {};
    const originalSource = source.original_source || {};
    
    // If there's an original source but no current source name, show popup
    return originalSource.name && !source.name;
}

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
 * Show detailed email sent notification as JavaScript popup
 */
function showEmailSentNotification(recipientName, recipientEmail, message, recipeName) {
    console.log('showEmailSentNotification called with:', {recipientName, recipientEmail, message, recipeName});
    
    const displayName = recipientName || 'Recipient';
    const displayMessage = message || 'No custom message';
    
    const popupContent = `
📧 EMAIL SENT SUCCESSFULLY!

📬 TO: ${displayName} (${recipientEmail})
🍽️ RECIPE: ${recipeName}
💬 MESSAGE: "${displayMessage}"

✅ The recipe has been sent to the recipient.
    `.trim();
    
    alert(popupContent);
}

/**
 * Show email error notification as JavaScript popup
 */
function showEmailErrorNotification(errorMessage, recipientEmail) {
    console.log('showEmailErrorNotification called with:', {errorMessage, recipientEmail});
    
    const popupContent = `
❌ EMAIL FAILED TO SEND

📬 TO: ${recipientEmail}
🚫 ERROR: ${errorMessage}

Please check the email address and try again.
    `.trim();
    
    alert(popupContent);
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

