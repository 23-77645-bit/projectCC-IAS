let courses = [];
let students = [];

function showFlash(message, type) {
    const container = document.getElementById('flash-container');
    const flash = document.createElement('div');
    flash.className = `alert alert-${type === 'success' ? 'success' : 'danger'} flash-message`;
    flash.textContent = message;
    container.appendChild(flash);
    setTimeout(() => flash.remove(), 3000);
}

async function loadCourses() {
    try {
        const res = await fetch('/courses');
        const data = await res.json();
        courses = data || [];
        
        const addSelect = document.getElementById('addCourseSelect');
        const editSelect = document.getElementById('editCourseSelect');
        const filterCourse = document.getElementById('filterCourse');
        
        [addSelect, editSelect].forEach(select => {
            if (!select) return;
            select.innerHTML = '<option value="">Select Course</option>';
            courses.forEach(c => {
                select.innerHTML += `<option value="${c.id}">${c.name}</option>`;
            });
        });

        if (filterCourse) {
            filterCourse.innerHTML = '<option value="">All Courses</option>';
            courses.forEach(c => {
                filterCourse.innerHTML += `<option value="${c.id}">${c.name}</option>`;
            });
        }
    } catch (err) {
        console.error('Failed to load courses:', err);
    }
}

async function loadStudents() {
    const tbody = document.getElementById('students-table-body');
    if (!tbody) return;

    try {
        const res = await fetch('/api/students');
        const data = await res.json();
        students = data || [];

        tbody.innerHTML = '';
        students.forEach(s => {
            const qrPath = s.qr_image_path || `/static/images/qrcodes/${s.qr_data}.png`;
            tbody.innerHTML += `
                <tr>
                    <td><strong>${s.name}</strong></td>
                    <td>${s.email}</td>
                    <td>${s.course_name || '—'}</td>
                    <td><img src="${qrPath}" alt="QR" class="qr-thumb" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2250%22 height=%2250%22><rect fill=%22%23eee%22 width=%2250%22 height=%2250%22/></svg>'"></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="openEditModal(${s.id})">Edit</button>
                        <button class="btn btn-sm btn-outline-secondary me-1" onclick="downloadQR('${s.qr_data}', '${s.name}')">Download QR</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteStudent(${s.id}, '${s.name}')">Delete</button>
                    </td>
                </tr>
            `;
        });
    } catch (err) {
        console.error('Failed to load students:', err);
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">Failed to load students</td></tr>';
    }
}

document.getElementById('addStudentForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Add loading state
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creating...';
    submitBtn.disabled = true;

    try {
        const res = await fetch('/api/students', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        
        if (res.ok) {
            showFlash('Student created successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('addStudentModal')).hide();
            form.reset();
            loadStudents();
        } else {
            showFlash(result.error || 'Failed to create student', 'danger');
        }
    } catch (err) {
        showFlash('Error creating student', 'danger');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

document.getElementById('uploadCsvForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const progressDiv = document.getElementById('uploadProgress');

    progressDiv.classList.remove('d-none');

    try {
        const res = await fetch('/api/upload-csv', {
            method: 'POST',
            body: formData
        });
        const result = await res.json();

        if (res.ok) {
            showFlash(`Uploaded ${result.uploaded || 0} students successfully`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('uploadCsvModal')).hide();
            form.reset();
            loadStudents();
        } else {
            showFlash(result.error || 'Failed to upload CSV', 'danger');
        }
    } catch (err) {
        showFlash('Error uploading CSV', 'danger');
    } finally {
        progressDiv.classList.add('d-none');
    }
});

function openEditModal(studentId) {
    const student = students.find(s => s.id === studentId);
    if (!student) return;

    document.getElementById('editStudentId').value = student.id;
    document.getElementById('editName').value = student.name;
    document.getElementById('editEmail').value = student.email;
    document.getElementById('editCourseSelect').value = student.course_id || '';

    new bootstrap.Modal(document.getElementById('editStudentModal')).show();
}

document.getElementById('editStudentForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const studentId = document.getElementById('editStudentId').value;
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const data = {
        name: document.getElementById('editName').value,
        email: document.getElementById('editEmail').value,
        course_id: document.getElementById('editCourseSelect').value
    };
    
    // Add loading state
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Updating...';
    submitBtn.disabled = true;

    try {
        const res = await fetch(`/students/${studentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();

        if (res.ok) {
            showFlash('Student updated successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('editStudentModal')).hide();
            loadStudents();
        } else {
            showFlash(result.error || 'Failed to update student', 'danger');
        }
    } catch (err) {
        showFlash('Error updating student', 'danger');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

async function deleteStudent(studentId, studentName) {
    if (!confirm(`Are you sure you want to delete ${studentName}? This will also delete their QR code.`)) {
        return;
    }

    try {
        const res = await fetch(`/students/${studentId}`, {
            method: 'DELETE'
        });
        const result = await res.json();

        if (res.ok) {
            showFlash('Student deleted successfully', 'success');
            loadStudents();
        } else {
            showFlash(result.error || 'Failed to delete student', 'danger');
        }
    } catch (err) {
        showFlash('Error deleting student', 'danger');
    }
}

function downloadQR(qrData, studentName) {
    const link = document.createElement('a');
    link.href = `/static/images/qrcodes/${qrData}.png`;
    link.download = `${studentName.replace(/\s+/g, '_')}_QR.png`;
    link.click();
}

document.addEventListener('DOMContentLoaded', () => {
    loadCourses();
    loadStudents();
});
