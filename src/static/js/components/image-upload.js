class ImageUploadManager {
    constructor() {
        this.init();
    }

    init() {
        ['image1', 'image2', 'image3'].forEach((inputId, index) => {
            const input = document.getElementById(`id_${inputId}`);
            if (input) this.setupImageInput(input, index + 1);
        });
    }

    setupImageInput(input, imageNumber) {
        const slot = input.closest('.tf-media-slot') || this.wrapInput(input);
        input.classList.add('tf-media-slot__input');

        let drop = slot.querySelector('.tf-media-slot__drop');
        if (!drop) {
            drop = document.createElement('label');
            drop.className = 'tf-media-slot__drop';
            drop.setAttribute('for', input.id);
            drop.innerHTML = `
                <span class="material-symbols-outlined tf-media-slot__icon">add_photo_alternate</span>
                <span class="tf-media-slot__text">Add image</span>
                <span class="tf-media-slot__hint">JPG, PNG, GIF · max 10MB</span>
            `;
            input.insertAdjacentElement('afterend', drop);
        }

        let previewContainer = slot.querySelector('.image-preview-container');
        if (!previewContainer) {
            previewContainer = document.createElement('div');
            previewContainer.className = 'image-preview-container';
            previewContainer.id = `preview-container-${imageNumber}`;
            slot.appendChild(previewContainer);
        }

        input.addEventListener('change', (e) => this.handleImageChange(e, imageNumber, slot));
    }

    wrapInput(input) {
        const slot = document.createElement('div');
        slot.className = 'tf-media-slot';
        input.parentNode.insertBefore(slot, input);
        slot.appendChild(input);
        return slot;
    }

    handleImageChange(event, imageNumber, slot) {
        const file = event.target.files[0];
        const previewContainer = document.getElementById(`preview-container-${imageNumber}`);
        previewContainer.innerHTML = '';
        slot.classList.remove('has-preview');

        if (!file) return;

        if (!file.type.startsWith('image/')) {
            this.showError(previewContainer, 'Please select a valid image file.');
            event.target.value = '';
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            this.showError(previewContainer, 'Image size must be less than 10MB.');
            event.target.value = '';
            return;
        }

        this.createPreview(file, previewContainer, event.target, slot);
    }

    createPreview(file, container, input, slot) {
        const reader = new FileReader();
        reader.onload = (e) => {
            slot.classList.add('has-preview');
            const previewDiv = document.createElement('div');
            previewDiv.className = 'image-preview';
            previewDiv.innerHTML = `
                <div class="image-preview__frame">
                    <img src="${e.target.result}" alt="">
                    <button type="button" class="image-preview__remove" title="Remove image" aria-label="Remove image">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
            `;
            previewDiv.querySelector('.image-preview__remove').addEventListener('click', () => {
                input.value = '';
                container.innerHTML = '';
                slot.classList.remove('has-preview');
            });
            container.appendChild(previewDiv);
        };
        reader.readAsDataURL(file);
    }

    showError(container, message) {
        container.innerHTML = `<div class="image-upload-error" role="alert">${this.escapeHtml(message)}</div>`;
    }

    escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ImageUploadManager();
});
