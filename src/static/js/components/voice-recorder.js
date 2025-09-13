class VoiceRecorder {
    constructor(containerId, fileInputId) {
        this.container = document.getElementById(containerId);
        this.fileInput = document.getElementById(fileInputId);
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.recordingStartTime = null;
        this.timerInterval = null;
        this.animationInterval = null;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.currentAudio = null;
        
        this.init();
    }
    
    init() {
        this.createRecorderHTML();
        this.bindEvents();
        this.checkMicrophonePermission();
    }
    
    createRecorderHTML() {
        this.container.innerHTML = `
            <div class="voice-recorder" id="voiceRecorderContainer">
                <div class="voice-recorder-controls">
                    <button type="button" class="record-button" id="recordButton">
                        <span class="material-symbols-outlined">mic</span>
                    </button>
                    <div class="recording-timer" id="recordingTimer">0:00</div>
                    <div class="waveform-container" id="waveformContainer">
                        <div class="waveform" id="waveform">
                            <div class="text-muted">Hold to record voice message</div>
                        </div>
                    </div>
                    <div class="recording-actions" id="recordingActions" style="display: none;">
                        <button type="button" class="action-button delete-button" id="deleteButton">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </div>
                </div>
                <div class="voice-preview" id="voicePreview">
                    <div class="voice-preview-controls">
                        <button type="button" class="action-button play-button" id="previewPlayButton">
                            <span class="material-symbols-outlined">play_arrow</span>
                        </button>
                        <div class="playback-waveform" id="playbackWaveform">
                            <div class="playback-progress" id="playbackProgress"></div>
                        </div>
                        <span class="recording-info" id="recordingDuration">0:00</span>
                    </div>
                    <div class="recording-info" id="recordingSize"></div>
                </div>
            </div>
        `;
    }
    
    bindEvents() {
        const recordButton = document.getElementById('recordButton');
        const deleteButton = document.getElementById('deleteButton');
        const previewPlayButton = document.getElementById('previewPlayButton');
        const playbackWaveform = document.getElementById('playbackWaveform');
        
        // Record button events
        recordButton.addEventListener('mousedown', () => this.startRecording());
        recordButton.addEventListener('mouseup', () => this.stopRecording());
        recordButton.addEventListener('mouseleave', () => this.stopRecording());
        recordButton.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        recordButton.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopRecording();
        });
        
        // Action buttons
        deleteButton.addEventListener('click', () => this.deleteRecording());
        previewPlayButton.addEventListener('click', () => this.togglePreviewPlayback());
        
        // Playback waveform click
        playbackWaveform.addEventListener('click', (e) => this.seekAudio(e));
    }
    
    async checkMicrophonePermission() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop());
            console.log('Microphone permission granted');
        } catch (error) {
            console.error('Microphone permission denied:', error);
            this.showError('Microphone access is required for voice recording');
        }
    }
    
    async startRecording() {
        if (this.isRecording) return;
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                }
            });
            
            this.isRecording = true;
            this.audioChunks = [];
            this.recordingStartTime = Date.now();
            
            // Setup MediaRecorder
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.processRecording();
                stream.getTracks().forEach(track => track.stop());
            };
            
            // Setup audio visualization
            this.setupAudioVisualization(stream);
            
            // Start recording
            this.mediaRecorder.start(100);
            this.startTimer();
            this.updateUI(true);
            
        } catch (error) {
            console.error('Error starting recording:', error);
            this.showError('Failed to start recording. Please check your microphone.');
        }
    }
    
    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;
        
        this.isRecording = false;
        this.mediaRecorder.stop();
        this.stopTimer();
        this.stopVisualization();
        this.updateUI(false);
    }
    
    setupAudioVisualization(stream) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        this.microphone = this.audioContext.createMediaStreamSource(stream);
        
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.8;
        this.microphone.connect(this.analyser);
        
        this.createWaveformBars();
        this.startVisualization();
    }
    
    createWaveformBars() {
        const waveform = document.getElementById('waveform');
        waveform.innerHTML = '';
        
        for (let i = 0; i < 50; i++) {
            const bar = document.createElement('div');
            bar.className = 'waveform-bar';
            bar.style.height = '4px';
            waveform.appendChild(bar);
        }
    }
    
    startVisualization() {
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        const bars = document.querySelectorAll('.waveform-bar');
        
        const animate = () => {
            if (!this.isRecording) return;
            
            this.analyser.getByteFrequencyData(dataArray);
            
            bars.forEach((bar, index) => {
                const value = dataArray[Math.floor(index * bufferLength / bars.length)];
                const height = Math.max(4, (value / 255) * 30);
                bar.style.height = `${height}px`;
                bar.classList.toggle('active', value > 50);
            });
            
            this.animationInterval = requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    stopVisualization() {
        if (this.animationInterval) {
            cancelAnimationFrame(this.animationInterval);
            this.animationInterval = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
    }
    
    startTimer() {
        const timerElement = document.getElementById('recordingTimer');
        
        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.recordingStartTime;
            const seconds = Math.floor(elapsed / 1000);
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            
            timerElement.textContent = `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }, 100);
    }
    
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }
    
    processRecording() {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        const audioFile = new File([audioBlob], `voice_recording_${Date.now()}.webm`, {
            type: 'audio/webm'
        });
        
        // Set the file to the input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(audioFile);
        this.fileInput.files = dataTransfer.files;
        
        // Create audio URL for preview
        const audioUrl = URL.createObjectURL(audioBlob);
        this.currentAudio = new Audio(audioUrl);
        
        // Show preview
        this.showPreview(audioFile);
        
        // Trigger change event for form validation
        this.fileInput.dispatchEvent(new Event('change'));
    }
    
    showPreview(audioFile) {
        const preview = document.getElementById('voicePreview');
        const durationElement = document.getElementById('recordingDuration');
        const sizeElement = document.getElementById('recordingSize');
        
        // Calculate duration and size
        const duration = Math.floor((Date.now() - this.recordingStartTime) / 1000);
        const minutes = Math.floor(duration / 60);
        const seconds = duration % 60;
        const fileSize = (audioFile.size / 1024).toFixed(1);
        
        durationElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        sizeElement.textContent = `Size: ${fileSize} KB`;
        
        preview.classList.add('show');
        document.getElementById('recordingActions').style.display = 'flex';
    }
    
    deleteRecording() {
        // Clear the file input
        this.fileInput.value = '';
        
        // Hide preview
        document.getElementById('voicePreview').classList.remove('show');
        document.getElementById('recordingActions').style.display = 'none';
        
        // Reset waveform
        const waveform = document.getElementById('waveform');
        waveform.innerHTML = '<div class="text-muted">Hold to record voice message</div>';
        
        // Reset timer
        document.getElementById('recordingTimer').textContent = '0:00';
        
        // Clean up audio
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
    }
    
    togglePreviewPlayback() {
        const playButton = document.getElementById('previewPlayButton');
        const icon = playButton.querySelector('span');
        
        if (!this.currentAudio) return;
        
        if (this.currentAudio.paused) {
            this.currentAudio.play();
            icon.textContent = 'pause';
            
            this.currentAudio.addEventListener('ended', () => {
                icon.textContent = 'play_arrow';
                document.getElementById('playbackProgress').style.width = '0%';
            });
            
            // Update progress
            const updateProgress = () => {
                if (!this.currentAudio.paused) {
                    const progress = (this.currentAudio.currentTime / this.currentAudio.duration) * 100;
                    document.getElementById('playbackProgress').style.width = `${progress}%`;
                    requestAnimationFrame(updateProgress);
                }
            };
            updateProgress();
            
        } else {
            this.currentAudio.pause();
            icon.textContent = 'play_arrow';
        }
    }
    
    seekAudio(event) {
        if (!this.currentAudio) return;
        
        const waveform = event.currentTarget;
        const rect = waveform.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const percentage = x / rect.width;
        const newTime = percentage * this.currentAudio.duration;
        
        this.currentAudio.currentTime = newTime;
        document.getElementById('playbackProgress').style.width = `${percentage * 100}%`;
    }
    
    updateUI(recording) {
        const recordButton = document.getElementById('recordButton');
        const container = document.getElementById('voiceRecorderContainer');
        const icon = recordButton.querySelector('span');
        
        if (recording) {
            recordButton.classList.add('recording');
            container.classList.add('recording');
            icon.textContent = 'stop';
        } else {
            recordButton.classList.remove('recording');
            container.classList.remove('recording');
            icon.textContent = 'mic';
        }
    }
    
    showError(message) {
        const waveform = document.getElementById('waveform');
        waveform.innerHTML = `<div class="text-danger">${message}</div>`;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if voice recorder elements exist
    if (document.getElementById('voiceRecorderContainer') && document.getElementById('id_voice')) {
        new VoiceRecorder('voiceRecorderContainer', 'id_voice');
    }
});
