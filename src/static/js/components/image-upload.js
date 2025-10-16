class ImageUploadManager {
    constructor() {
        this.init();
    }

    init() {
        // Initialize image upload handlers for each input
        const imageInputs = ['image1', 'image2', 'image3'];
        
        imageInputs.forEach((inputId, index) => {
            const input = document.getElementById(`id_${inputId}`);
            if (input) {
                this.setupImageInput(input, index + 1);
            }
        });
    }

    setupImageInput(input, imageNumber) {
        // Create preview container
        const previewContainer = document.createElement('div');
        previewContainer.className = 'image-preview-container mt-2';
        previewContainer.id = `preview-container-${imageNumber}`;
        
        // Insert preview container after the input
        input.parentNode.insertBefore(previewContainer, input.nextSibling);
        
        // Add change event listener
        input.addEventListener('change', (e) => {
            this.handleImageChange(e, imageNumber);
        });
    }

    handleImageChange(event, imageNumber) {
        const file = event.target.files[0];
        const previewContainer = document.getElementById(`preview-container-${imageNumber}`);
        
        // Clear previous preview
        previewContainer.innerHTML = '';
        
        if (file) {
            // Validate file type
            if (!file.type.startsWith('image/')) {
                this.showError(previewContainer, 'Please select a valid image file.');
                event.target.value = '';
                return;
            }
            
            // Validate file size (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                this.showError(previewContainer, 'Image size must be less than 5MB.');
                event.target.value = '';
                return;
            }
            
            // Create preview
            this.createPreview(file, previewContainer, event.target);
        }
    }

    createPreview(file, container, input) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            const previewDiv = document.createElement('div');
            previewDiv.className = 'image-preview';
            
            previewDiv.innerHTML = `
                <div class="position-relative">
                    <img src="${e.target.result}" alt="Preview" class="img-thumbnail" style="max-width: 150px; max-height: 150px;">
                    <button type="button" class="btn btn-danger btn-sm position-absolute top-0 end-0 m-1 remove-image" 
                            style="padding: 2px 6px; font-size: 12px;" title="Remove image">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <small class="text-muted d-block mt-1">${file.name}</small>
                <small class="text-muted">${this.formatFileSize(file.size)}</small>
            `;
            
            // Add remove functionality
            const removeBtn = previewDiv.querySelector('.remove-image');
            removeBtn.addEventListener('click', () => {
                input.value = '';
                container.innerHTML = '';
            });
            
            container.appendChild(previewDiv);
        };
        
        reader.readAsDataURL(file);
    }

    showError(container, message) {
        container.innerHTML = `
            <div class="alert alert-danger alert-sm p-2 mt-2" role="alert">
                <small>${message}</small>
            </div>
        `;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ImageUploadManager();
});
