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
        const res = await fetch('/courses');
        const data = await res.json();
        courses = data || [];
    } catch (err) {
        console.error('Failed to load courses:', err);
    }
}

async function loadCoursesTable() {
    const tbody = document.getElementById('courses-table-body');
    if (!tbody) return;

    try {
        const res = await fetch('/courses');
        const data = await res.json();
        courses = data || [];

        tbody.innerHTML = '';
        courses.forEach(c => {
            const canDelete = c.student_count === 0;
            tbody.innerHTML += `
                <tr>
                    <td><strong>${c.name}</strong></td>
                    <td>${c.section || '—'}</td>
                    <td>${c.schedule || '—'}</td>
                    <td><span class="badge ${c.student_count > 0 ? 'bg-primary' : 'bg-secondary'}">${c.student_count}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="openEditModal(${c.id})">Edit</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteCourse(${c.id}, '${c.name}', ${c.student_count})" 
                            ${!canDelete ? 'disabled title="Cannot delete course with enrolled students"' : ''}>
                            Delete
                        </button>
                    </td>
                </tr>
            `;
        });
    } catch (err) {
        console.error('Failed to load courses:', err);
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">Failed to load courses</td></tr>';
    }
}

document.getElementById('addCourseForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const data = {
        name: form.name.value,
        section: form.section.value,
        schedule: form.schedule.value
    };
    
    // Add loading state
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creating...';
    submitBtn.disabled = true;

    try {
        const res = await fetch('/courses', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();

        if (res.ok) {
            showFlash('Course created successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('addCourseModal')).hide();
            form.reset();
            loadCoursesTable();
        } else {
            showFlash(result.error || 'Failed to create course', 'danger');
        }
    } catch (err) {
        showFlash('Error creating course', 'danger');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

function openEditModal(courseId) {
    const course = courses.find(c => c.id === courseId);
    if (!course) return;

    document.getElementById('editCourseId').value = course.id;
    document.getElementById('editName').value = course.name;
    document.getElementById('editSection').value = course.section || '';
    document.getElementById('editSchedule').value = course.schedule || '';

    new bootstrap.Modal(document.getElementById('editCourseModal')).show();
}

document.getElementById('editCourseForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const courseId = document.getElementById('editCourseId').value;
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const data = {
        name: document.getElementById('editName').value,
        section: document.getElementById('editSection').value,
        schedule: document.getElementById('editSchedule').value
    };
    
    // Add loading state
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Updating...';
    submitBtn.disabled = true;

    try {
        const res = await fetch(`/courses/${courseId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();

        if (res.ok) {
            showFlash('Course updated successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('editCourseModal')).hide();
            loadCoursesTable();
        } else {
            showFlash(result.error || 'Failed to update course', 'danger');
        }
    } catch (err) {
        showFlash('Error updating course', 'danger');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

async function deleteCourse(courseId, courseName, studentCount) {
    if (studentCount > 0) {
        showFlash(`Cannot delete "${courseName}" - it has ${studentCount} enrolled student(s)`, 'danger');
        return;
    }

    if (!confirm(`Are you sure you want to delete "${courseName}"?`)) {
        return;
    }

    try {
        const res = await fetch(`/courses/${courseId}`, {
            method: 'DELETE'
        });
        const result = await res.json();

        if (res.ok) {
            showFlash('Course deleted successfully', 'success');
            loadCoursesTable();
        } else {
            showFlash(result.error || 'Failed to delete course', 'danger');
        }
    } catch (err) {
        showFlash('Error deleting course', 'danger');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadCourses();
    loadCoursesTable();
});
