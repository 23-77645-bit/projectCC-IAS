let scanBusy = false;
let html5QrCodeScanner = null;
let videoElement = null;
let canvasElement = null;

function getToken() {
    const token = sessionStorage.getItem('token');
    if (token) return token;
    const match = document.cookie.match(/token=([^;]+)/);
    return match ? match[1] : null;
}

function updateChecklist(step, status) {
    const item = document.getElementById(`checklist-${step}`);
    if (!item) return;
    
    item.classList.remove('pending', 'detected', 'verified', 'failed');
    
    if (status === 'pending') {
        item.querySelector('.badge').textContent = '-';
        item.querySelector('.checklist-text').classList.add('text-muted');
    } else if (status === 'detected') {
        item.classList.add('detected');
        item.querySelector('.badge').textContent = '✓';
    } else if (status === 'verified') {
        item.classList.add('verified');
        item.querySelector('.badge').textContent = '✓';
    } else if (status === 'failed') {
        item.classList.add('failed');
        item.querySelector('.badge').textContent = '✕';
    }
}

function resetChecklist() {
    updateChecklist('qr', 'pending');
    updateChecklist('face', 'pending');
    updateChecklist('identity', 'pending');
}

function captureFrame() {
    if (!videoElement || !canvasElement) return null;
    
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    
    const ctx = canvasElement.getContext('2d');
    ctx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
    
    let dataUrl = canvasElement.toDataURL('image/jpeg', 0.8);
    
    if (dataUrl.startsWith('data:image/jpeg;base64,')) {
        dataUrl = dataUrl.substring('data:image/jpeg;base64,'.length);
    }
    
    return dataUrl;
}

function updateLastScanTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    document.getElementById('last-scan-time').textContent = timeStr;
}

function renderResult(data) {
    const resultEl = document.getElementById('scan-result');
    
    if (!data) {
        resultEl.innerHTML = '<p class="text-muted text-center py-4">Waiting for scan...</p>';
        return;
    }
    
    const studentName = data.student_name || 'Unknown';
    const courseName = data.course_name || 'No course';
    const status = data.status || '';
    const verification = data.verification || 'qr_only';
    
    let cardClass = 'success-card';
    let badgeText = '✅ Verified by QR + Face';
    
    if (verification === 'qr_only') {
        badgeText = '📱 QR Only Mode';
    }
    
    let statusMessage = '';
    if (status === 'time_in_recorded') {
        statusMessage = `Checked in at ${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    } else if (status === 'time_out_recorded') {
        statusMessage = `Checked out at ${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    } else if (status === 'already_complete') {
        cardClass = 'warning-card';
        statusMessage = 'Attendance already recorded for today';
    }
    
    resultEl.innerHTML = `
        <div class="result-card ${cardClass} rounded p-3">
            <div class="d-flex justify-content-between align-items-start mb-2">
                <h5 class="fw-bold mb-0">${studentName}</h5>
                <span class="verification-badge">${badgeText}</span>
            </div>
            <p class="text-muted small mb-2">${courseName}</p>
            <p class="mb-0 small">${statusMessage}</p>
        </div>
    `;
    
    updateLastScanTime();
    
    setTimeout(() => {
        resultEl.innerHTML = '<p class="text-muted text-center py-4">Waiting for scan...</p>';
        resetChecklist();
    }, 4000);
}

function renderError(errorCode, message) {
    const resultEl = document.getElementById('scan-result');
    
    let cardClass = 'error-card';
    let icon = '⚠️';
    let title = 'Scan Error';
    
    if (errorCode === 'no_face') {
        cardClass = 'warning-card';
        icon = '👤';
        title = 'No Face Detected';
    } else if (errorCode === 'face_mismatch') {
        icon = '❌';
        title = 'Face Mismatch';
    } else if (errorCode === 'invalid_qr') {
        icon = '📱';
        title = 'Invalid QR Code';
    } else if (errorCode === 'already_complete') {
        cardClass = 'warning-card';
        icon = 'ℹ️';
        title = 'Already Recorded';
    }
    
    resultEl.innerHTML = `
        <div class="result-card ${cardClass} rounded p-3">
            <div class="d-flex align-items-center mb-2">
                <span class="fs-4 me-2">${icon}</span>
                <h5 class="fw-bold mb-0">${title}</h5>
            </div>
            <p class="mb-0 small">${message}</p>
        </div>
    `;
    
    updateLastScanTime();
    
    setTimeout(() => {
        resultEl.innerHTML = '<p class="text-muted text-center py-4">Waiting for scan...</p>';
        resetChecklist();
    }, 3000);
}

function onSimultaneousScan(qrData) {
    if (scanBusy) return;
    
    scanBusy = true;
    document.getElementById('qr-status-dot').classList.remove('bg-primary');
    document.getElementById('qr-status-dot').classList.add('bg-warning');
    
    updateChecklist('qr', 'detected');
    updateChecklist('face', 'detected');
    
    const frameBase64 = captureFrame();
    
    if (!frameBase64) {
        renderError('capture_error', 'Failed to capture camera frame');
        scanBusy = false;
        return;
    }
    
    fetch('/scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getToken()
        },
        body: JSON.stringify({
            qr_data: qrData,
            frame: frameBase64
        })
    })
    .then(async (response) => {
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Unable to process scan');
        }
        
        if (result.verification === 'qr_and_face') {
            updateChecklist('identity', 'verified');
        } else {
            updateChecklist('identity', 'detected');
        }
        
        renderResult(result);
    })
    .catch((err) => {
        console.error('Scan error:', err);
        const errorCode = err.message || 'unknown_error';
        
        if (errorCode === 'no_face') {
            updateChecklist('face', 'failed');
        } else if (errorCode === 'face_mismatch') {
            updateChecklist('identity', 'failed');
        } else if (errorCode === 'invalid_qr') {
            updateChecklist('qr', 'failed');
        }
        
        renderError(errorCode, result?.message || err.message);
    })
    .finally(() => {
        setTimeout(() => {
            scanBusy = false;
            document.getElementById('qr-status-dot').classList.remove('bg-warning');
            document.getElementById('qr-status-dot').classList.add('bg-primary');
        }, 3000);
    });
}

function onQrSuccess(decodedText) {
    if (!scanBusy && decodedText) {
        onSimultaneousScan(decodedText);
    }
}

function onQrError(errorMessage) {
    // Silent - errors are expected when no QR is in frame
}

async function startCamera() {
    videoElement = document.getElementById('camera-feed');
    canvasElement = document.getElementById('capture-canvas');
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment',
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        });
        
        videoElement.srcObject = stream;
        
        document.getElementById('camera-status').textContent = 'Camera Active';
        
        return new Promise((resolve) => {
            videoElement.onloadedmetadata = () => {
                videoElement.play();
                resolve();
            };
        });
    } catch (err) {
        console.error('Camera error:', err);
        document.getElementById('camera-status').textContent = 'Camera Error';
        document.querySelector('.status-dot.bg-success').classList.remove('bg-success');
        document.querySelector('.status-dot').classList.add('bg-danger');
        
        const resultEl = document.getElementById('scan-result');
        resultEl.innerHTML = `
            <div class="text-center py-4">
                <p class="text-danger">Unable to access camera</p>
                <p class="text-muted small">Please ensure camera permissions are granted</p>
            </div>
        `;
        throw err;
    }
}

async function startQrDetection() {
    const qrReaderElement = document.getElementById('qr-reader-hidden');
    
    html5QrCodeScanner = new Html5Qrcode(qrReaderElement.id);
    
    const config = {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0
    };
    
    try {
        await html5QrCodeScanner.start(
            { facingMode: 'environment' },
            config,
            onQrSuccess,
            onQrError
        );
        
        document.getElementById('qr-status').textContent = 'QR Detection Active';
    } catch (err) {
        console.error('QR detection error:', err);
        document.getElementById('qr-status').textContent = 'QR Detection Error';
        document.getElementById('qr-status-dot').classList.remove('bg-primary');
        document.getElementById('qr-status-dot').classList.add('bg-danger');
    }
}

async function initScanner() {
    resetChecklist();
    
    try {
        await startCamera();
        await startQrDetection();
    } catch (err) {
        console.error('Scanner initialization failed:', err);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initScanner();
});
