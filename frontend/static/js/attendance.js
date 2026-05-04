let attendanceRecords = [];
let courses = [];

function showFlash(message, type) {
    const container = document.getElementById('flash-container');
    if (!container) return;
    const flash = document.createElement('div');
    flash.className = `alert alert-${type === 'success' ? 'success' : 'danger'} flash-message`;
    flash.textContent = message;
    container.appendChild(flash);
    setTimeout(() => flash.remove(), 3000);
}

async function loadCourses() {
    try {
        const res = await fetch('/api/courses');
        const data = await res.json();
        courses = data.courses || [];

        const filterCourse = document.getElementById('filterCourse');
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

async function loadAttendance(filters = {}) {
    const tbody = document.getElementById('attendance-table-body');
    if (!tbody) return;

    let url = '/api/attendance?';
    if (filters.date) url += `date=${filters.date}&`;
    if (filters.course_id) url += `course_id=${filters.course_id}&`;
    if (filters.status) url += `status=${filters.status}&`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        attendanceRecords = data.records || [];
        const summary = data.summary || { present: 0, absent: 0 };

        tbody.innerHTML = '';
        if (attendanceRecords.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No attendance records found</td></tr>';
        } else {
            attendanceRecords.forEach(r => {
                const statusBadge = r.status === 'present' 
                    ? '<span class="badge badge-present">Present</span>' 
                    : '<span class="badge badge-absent">Absent</span>';
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${r.student_name}</strong></td>
                        <td>${r.course_name || '—'}</td>
                        <td>${r.date}</td>
                        <td>${r.time_in || '—'}</td>
                        <td>${r.time_out || '—'}</td>
                        <td>${statusBadge}</td>
                    </tr>
                `;
            });
        }

        const tfoot = document.getElementById('attendance-summary');
        if (tfoot) {
            tfoot.innerHTML = `
                <tr>
                    <td colspan="6" class="text-end">
                        <strong>Summary:</strong> 
                        <span class="badge badge-present me-2">Present: ${summary.present}</span>
                        <span class="badge badge-absent">Absent: ${summary.absent}</span>
                    </td>
                </tr>
            `;
        }
    } catch (err) {
        console.error('Failed to load attendance:', err);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">Failed to load attendance records</td></tr>';
    }
}

document.getElementById('applyFilterBtn')?.addEventListener('click', () => {
    const filters = {
        date: document.getElementById('filterDate').value,
        course_id: document.getElementById('filterCourse').value,
        status: document.getElementById('filterStatus').value
    };
    loadAttendance(filters);
});

document.getElementById('exportCsvBtn')?.addEventListener('click', async () => {
    const filters = {
        date: document.getElementById('filterDate').value,
        course_id: document.getElementById('filterCourse').value,
        status: document.getElementById('filterStatus').value
    };

    let url = '/api/attendance/export?';
    if (filters.date) url += `date=${filters.date}&`;
    if (filters.course_id) url += `course_id=${filters.course_id}&`;
    if (filters.status) url += `status=${filters.status}&`;

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('Export failed');
        
        const blob = await res.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `attendance_export_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(link.href);
        
        showFlash('Attendance exported successfully', 'success');
    } catch (err) {
        showFlash('Failed to export attendance', 'danger');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadCourses();
    loadAttendance();
    
    document.getElementById('filterDate').valueAsDate = new Date();
});
