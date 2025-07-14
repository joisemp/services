/**
 * Transportation App JavaScript
 * Handles dynamic interactions, form submissions, and UI enhancements
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all transportation app features
    initializeVehicleForm();
    initializeMaintenanceForm();
    initializeDocumentUpload();
    initializeModalHandlers();
    initializeFilterHandlers();
    initializeSearchHandlers();
    initializeComponentHandlers();
});

/**
 * Vehicle Form Enhancements
 */
function initializeVehicleForm() {
    const vehicleForm = document.getElementById('vehicleForm');
    if (!vehicleForm) return;

    // Handle form submission with htmx
    vehicleForm.addEventListener('htmx:beforeSend', function(event) {
        showFormLoading(vehicleForm);
        disableFormSubmit(vehicleForm);
    });

    vehicleForm.addEventListener('htmx:afterRequest', function(event) {
        hideFormLoading(vehicleForm);
        enableFormSubmit(vehicleForm);

        if (event.detail.successful) {
            showToast('Vehicle saved successfully!', 'success');
        } else {
            showToast('Error saving vehicle. Please check the form.', 'error');
        }
    });

    // Dynamic field validation
    const requiredFields = vehicleForm.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        field.addEventListener('blur', function() {
            validateField(field);
        });

        field.addEventListener('input', function() {
            clearFieldError(field);
        });
    });
}

/**
 * Maintenance Form Enhancements
 */
function initializeMaintenanceForm() {
    const maintenanceForm = document.getElementById('maintenanceForm');
    if (!maintenanceForm) return;

    // Handle form submission
    maintenanceForm.addEventListener('htmx:beforeSend', function(event) {
        showFormLoading(maintenanceForm);
    });

    maintenanceForm.addEventListener('htmx:afterRequest', function(event) {
        hideFormLoading(maintenanceForm);

        if (event.detail.successful) {
            showToast('Maintenance record saved successfully!', 'success');
        }
    });

    // Auto-calculate next service dates
    const serviceTypeField = maintenanceForm.querySelector('#id_service_type');
    const mileageField = maintenanceForm.querySelector('#id_current_mileage');
    
    if (serviceTypeField && mileageField) {
        [serviceTypeField, mileageField].forEach(field => {
            field.addEventListener('change', function() {
                autoCalculateNextService();
            });
        });
    }
}

/**
 * Document Upload Enhancements
 */
function initializeDocumentUpload() {
    const fileInputs = document.querySelectorAll('.file-upload input[type="file"]');
    
    fileInputs.forEach(input => {
        const uploadArea = input.closest('.file-upload-area');
        const preview = input.parentNode.querySelector('.file-preview');

        // Drag and drop handlers
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                showFilePreview(input, files[0], preview);
            }
        });

        // File selection handler
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                showFilePreview(input, file, preview);
            }
        });
    });
}

/**
 * Modal Handlers
 */
function initializeModalHandlers() {
    // Add component modal
    const addComponentBtn = document.getElementById('addComponentBtn');
    const componentModal = document.getElementById('componentModal');
    
    if (addComponentBtn && componentModal) {
        addComponentBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showModal(componentModal);
        });
    }

    // Close modal handlers
    document.querySelectorAll('.modal .close, .modal [data-dismiss="modal"]').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            const modal = closeBtn.closest('.modal');
            hideModal(modal);
        });
    });

    // Close modal on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                hideModal(modal);
            }
        });
    });
}

/**
 * Filter Handlers
 */
function initializeFilterHandlers() {
    const filterSelects = document.querySelectorAll('.filter-controls select');
    
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            const form = select.closest('form');
            if (form) {
                // Trigger htmx request for filtered results
                htmx.trigger(form, 'submit');
            }
        });
    });
}

/**
 * Search Handlers
 */
function initializeSearchHandlers() {
    const searchInputs = document.querySelectorAll('.search-input-group input');
    
    searchInputs.forEach(input => {
        let searchTimeout;
        
        input.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            
            searchTimeout = setTimeout(() => {
                const form = input.closest('form');
                if (form) {
                    htmx.trigger(form, 'submit');
                }
            }, 300); // 300ms debounce
        });
    });
}

/**
 * Component Handlers
 */
function initializeComponentHandlers() {
    // Component card clicks
    document.querySelectorAll('.component-card').forEach(card => {
        card.addEventListener('click', function(e) {
            // Don't navigate if clicking on action buttons
            if (e.target.closest('.component-actions')) {
                return;
            }
            
            const detailUrl = card.dataset.detailUrl;
            if (detailUrl) {
                window.location.href = detailUrl;
            }
        });
    });
}

/**
 * Utility Functions
 */

function showFormLoading(form) {
    const loading = form.querySelector('.form-loading');
    if (loading) {
        loading.classList.add('active');
    }
}

function hideFormLoading(form) {
    const loading = form.querySelector('.form-loading');
    if (loading) {
        loading.classList.remove('active');
    }
}

function disableFormSubmit(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
    }
}

function enableFormSubmit(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span class="material-symbols-outlined me-2">save</span>Save';
    }
}

function validateField(field) {
    const value = field.value.trim();
    const isRequired = field.hasAttribute('required');
    
    if (isRequired && !value) {
        showFieldError(field, 'This field is required');
        return false;
    }
    
    // Additional validation based on field type
    if (field.type === 'email' && value && !isValidEmail(value)) {
        showFieldError(field, 'Please enter a valid email address');
        return false;
    }
    
    clearFieldError(field);
    return true;
}

function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    let feedback = field.parentNode.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.appendChild(feedback);
    }
    
    feedback.textContent = message;
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

function showFilePreview(input, file, preview) {
    if (!preview) return;
    
    preview.classList.add('show');
    
    const fileName = preview.querySelector('.file-details h6');
    const fileSize = preview.querySelector('.file-size');
    const progressBar = preview.querySelector('.progress-fill');
    
    if (fileName) fileName.textContent = file.name;
    if (fileSize) fileSize.textContent = formatFileSize(file.size);
    
    // Simulate upload progress
    if (progressBar) {
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 30;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
            }
            progressBar.style.width = progress + '%';
        }, 200);
    }
}

function showModal(modal) {
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function hideModal(modal) {
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

function showToast(message, type = 'info') {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <span class="material-symbols-outlined">${getToastIcon(type)}</span>
            <span class="toast-message">${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Show toast
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Hide toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 3000);
}

function getToastIcon(type) {
    const icons = {
        success: 'check_circle',
        error: 'error',
        warning: 'warning',
        info: 'info'
    };
    return icons[type] || icons.info;
}

function autoCalculateNextService() {
    // Auto-calculate next service dates based on service type and current mileage
    const serviceType = document.getElementById('id_service_type')?.value;
    const currentMileage = document.getElementById('id_current_mileage')?.value;
    const nextMileageField = document.getElementById('id_next_service_due_mileage');
    const nextDateField = document.getElementById('id_next_service_due_date');
    
    if (!serviceType || !currentMileage) return;
    
    // Service intervals (in miles and months)
    const serviceIntervals = {
        'oil_change': { miles: 5000, months: 6 },
        'tire_rotation': { miles: 7500, months: 6 },
        'brake_inspection': { miles: 15000, months: 12 },
        'transmission': { miles: 30000, months: 24 },
        'major_service': { miles: 60000, months: 36 }
    };
    
    const interval = serviceIntervals[serviceType];
    if (!interval) return;
    
    // Calculate next mileage
    if (nextMileageField) {
        const nextMileage = parseInt(currentMileage) + interval.miles;
        nextMileageField.value = nextMileage;
    }
    
    // Calculate next date
    if (nextDateField) {
        const nextDate = new Date();
        nextDate.setMonth(nextDate.getMonth() + interval.months);
        nextDateField.value = nextDate.toISOString().split('T')[0];
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// HTMX Event Handlers
document.addEventListener('htmx:afterSwap', function(event) {
    // Re-initialize components after htmx swaps content
    if (event.detail.target.id === 'vehicleList') {
        initializeFilterHandlers();
        initializeSearchHandlers();
    }
    
    if (event.detail.target.id === 'componentList') {
        initializeComponentHandlers();
    }
});

document.addEventListener('htmx:sendError', function(event) {
    showToast('Network error. Please check your connection.', 'error');
});

document.addEventListener('htmx:responseError', function(event) {
    showToast('Server error. Please try again.', 'error');
});
