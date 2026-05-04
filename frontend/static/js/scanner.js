let scanBusy = false;
let html5QrCodeScanner = null;

function renderResult(data, isError = false) {
    const resultEl = document.getElementById('scan-result');
    
    if (!data || isError) {
        resultEl.innerHTML = `
            <div class="text-center py-4">
                <p class="text-danger mb-2">${data?.error || 'Student not found'}</p>
                <p class="text-muted small">Please try scanning again</p>
            </div>
        `;
        return;
    }

    const student = data.student;
    const attendance = data.attendance;
    
    const timeIn = attendance?.time_in 
        ? new Date(attendance.time_in).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) 
        : 'N/A';
    const timeOut = attendance?.time_out 
        ? new Date(attendance.time_out).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) 
        : '—';
    const dateStr = attendance?.date 
        ? new Date(attendance.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) 
        : new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    
    const status = attendance?.status || 'present';
    const statusBadgeClass = status === 'present' ? 'bg-success' : 'bg-secondary';
    const isAlreadyRecorded = attendance?.time_in && !attendance?.time_out;

    resultEl.innerHTML = `
        <div class="card border-0" style="background-color: #f9f9f9;">
            <div class="card-body">
                <h5 class="fw-bold mb-1">${student.name}</h5>
                <p class="text-muted mb-3 small">${student.course_name || 'No course assigned'}</p>
                
                <div class="row g-2 mb-3">
                    <div class="col-6">
                        <span class="d-block text-muted small">Date</span>
                        <span class="fw-medium">${dateStr}</span>
                    </div>
                    <div class="col-6">
                        <span class="d-block text-muted small">Status</span>
                        <span class="badge ${statusBadgeClass}">${status}</span>
                    </div>
                </div>
                
                <div class="row g-2">
                    <div class="col-6">
                        <span class="d-block text-muted small">Time In</span>
                        <span class="fw-medium">${timeIn}</span>
                    </div>
                    <div class="col-6">
                        <span class="d-block text-muted small">Time Out</span>
                        <span class="fw-medium">${timeOut}</span>
                    </div>
                </div>
                
                ${isAlreadyRecorded 
                    ? '<div class="alert alert-warning mt-3 mb-0 small py-2">Already checked in. Scan again to check out.</div>' 
                    : ''}
            </div>
        </div>
    `;
}

function postScan(qrData) {
    if (scanBusy) {
        return;
    }
    
    scanBusy = true;
    
    fetch('/scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ qr_data: qrData })
    })
    .then(async (response) => {
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Unable to process scan');
        }
        
        renderResult(result, false);
    })
    .catch((err) => {
        console.error('Scan error:', err);
        renderResult({ error: err.message }, true);
    })
    .finally(() => {
        setTimeout(() => {
            scanBusy = false;
        }, 2000);
    });
}

function onScanSuccess(decodedText) {
    if (!scanBusy) {
        postScan(decodedText);
    }
}

function onScanError(errorMessage) {
    console.warn('Scanner warning:', errorMessage);
    // Show error in UI but don't stop scanner
    const resultEl = document.getElementById('scan-result');
    if (resultEl && !scanBusy) {
        resultEl.innerHTML = `
            <div class="text-center py-4">
                <p class="text-muted small">Waiting for valid QR code...</p>
            </div>
        `;
    }
}

function initScanner() {
    html5QrCodeScanner = new Html5Qrcode('qr-reader');
    
    const config = { 
        fps: 10, 
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0
    };
    
    html5QrCodeScanner.start(
        { facingMode: 'environment' },
        config,
        onScanSuccess,
        onScanError
    )
    .catch((err) => {
        console.error('Failed to start scanner:', err);
        const resultEl = document.getElementById('scan-result');
        resultEl.innerHTML = `
            <div class="text-center py-4">
                <p class="text-danger">Unable to access camera</p>
                <p class="text-muted small">Please ensure camera permissions are granted</p>
            </div>
        `;
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initScanner();
});
