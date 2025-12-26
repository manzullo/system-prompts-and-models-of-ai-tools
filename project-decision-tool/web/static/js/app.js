/**
 * Project Decision Tool - Frontend JavaScript
 */

// ==================== STATE ====================
let currentSection = 'dashboard';
let focusInterval = null;
let focusStartTime = null;
let focusDuration = 0;
let focusPaused = false;

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initEventListeners();
    loadDashboard();
});

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const section = item.dataset.section;
            navigateTo(section);
        });
    });
}

function navigateTo(section) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === section);
    });

    // Update sections
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.toggle('active', sec.id === section);
    });

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        decide: 'Cosa Fare?',
        focus: 'Focus Mode',
        projects: 'Progetti',
        tasks: 'Task',
        antiproc: 'Anti-Procrastinazione',
        achievements: 'Achievements'
    };
    document.getElementById('page-title').textContent = titles[section] || section;

    currentSection = section;

    // Load section data
    switch(section) {
        case 'dashboard': loadDashboard(); break;
        case 'projects': loadProjects(); break;
        case 'tasks': loadTasks(); break;
        case 'focus': loadFocusData(); break;
        case 'antiproc': loadAntiProc(); break;
        case 'achievements': loadAchievements(); break;
    }
}

function initEventListeners() {
    // Energy selector
    document.querySelectorAll('.energy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.energy-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Time selector
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Mood slider
    const moodSlider = document.getElementById('mood-slider');
    if (moodSlider) {
        moodSlider.addEventListener('input', (e) => {
            document.getElementById('mood-value').textContent = e.target.value;
        });
    }

    // Session type buttons
    document.querySelectorAll('.session-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.session-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Project sliders
    ['importance', 'urgency', 'excitement'].forEach(field => {
        const slider = document.getElementById(`project-${field}`);
        if (slider) {
            slider.addEventListener('input', (e) => {
                document.getElementById(`project-${field}-value`).textContent = e.target.value;
            });
        }
    });

    // Block reason buttons
    document.querySelectorAll('.reason-btn').forEach(btn => {
        btn.addEventListener('click', () => getIntervention(btn.dataset.reason));
    });
}

// ==================== API CALLS ====================
async function api(endpoint, options = {}) {
    const response = await fetch(`/api${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        body: options.body ? JSON.stringify(options.body) : undefined
    });
    return response.json();
}

// ==================== DASHBOARD ====================
async function loadDashboard() {
    loadProfile();
    loadTodayStats();
    loadProductivityScore();
    loadChallenges();
    loadInsights();
    getQuickDecision();
}

async function loadProfile() {
    const profile = await api('/profile');

    document.getElementById('profile-name').textContent = profile.username;
    document.getElementById('profile-level-name').textContent = profile.level_name;
    document.getElementById('profile-level-icon').textContent = profile.level_icon;
    document.getElementById('user-level-icon').textContent = profile.level_icon;
    document.getElementById('user-level').textContent = `Lv. ${profile.level}`;
    document.getElementById('user-points').textContent = profile.total_points.toLocaleString();

    document.getElementById('level-progress').style.width = `${profile.level_progress}%`;
    document.getElementById('level-progress-text').textContent = `${Math.round(profile.level_progress)}% al prossimo livello`;

    document.getElementById('profile-streak').textContent = profile.streak;
    document.getElementById('profile-tasks').textContent = profile.total_tasks;
    document.getElementById('profile-focus').textContent = profile.total_focus_minutes;

    document.getElementById('sidebar-streak').textContent = profile.streak;
}

async function loadTodayStats() {
    const stats = await api('/stats/today');

    document.getElementById('today-focus').textContent = stats.focus_minutes;
    document.getElementById('today-tasks').textContent = stats.tasks_completed;
    document.getElementById('today-points').textContent = stats.points_earned;
}

async function loadProductivityScore() {
    const data = await api('/stats/score');

    const circle = document.getElementById('score-circle-fill');
    circle.setAttribute('stroke-dasharray', `${data.score}, 100`);

    document.getElementById('score-value').textContent = data.score;
    document.getElementById('score-description').textContent = data.description;
}

async function loadChallenges() {
    const challenges = await api('/challenges');
    const container = document.getElementById('challenges-list');

    container.innerHTML = challenges.map(c => `
        <div class="challenge-item ${c.completed ? 'completed' : ''}">
            <span class="challenge-icon">${c.icon}</span>
            <div class="challenge-info">
                <div class="challenge-name">${c.name}</div>
                <div class="challenge-progress">
                    <div class="challenge-progress-fill" style="width: ${c.progress}%"></div>
                </div>
            </div>
            <span class="challenge-status">${c.current}/${c.goal}</span>
        </div>
    `).join('');
}

async function loadInsights() {
    const insights = await api('/insights');
    const container = document.getElementById('insights-list');

    container.innerHTML = insights.slice(0, 3).map(i => `
        <div class="insight-item">
            <span class="insight-icon">${i.icon}</span>
            <div class="insight-text">
                <div class="insight-title">${i.title}</div>
                <div class="insight-message">${i.message}</div>
            </div>
        </div>
    `).join('');
}

async function getQuickDecision() {
    const container = document.getElementById('quick-recommendation');
    container.innerHTML = '<p class="loading">Analizzando...</p>';

    const rec = await api('/decide', {
        method: 'POST',
        body: { mode: 'smart' }
    });

    if (rec.has_recommendation) {
        const name = rec.project?.name || rec.task?.name || 'Task';
        container.innerHTML = `
            <div class="recommendation-name">📌 ${name}</div>
            <ul class="recommendation-reasons">
                ${rec.reasoning.slice(0, 3).map(r => `<li>${r}</li>`).join('')}
            </ul>
        `;
    } else {
        container.innerHTML = `
            <p>Nessun progetto o task attivo.</p>
            <p>Crea il tuo primo progetto per iniziare!</p>
        `;
    }
}

// ==================== DECISION ====================
async function getDecision() {
    const energy = document.querySelector('.energy-btn.active')?.dataset.value || 'medium';
    const time = parseInt(document.querySelector('.time-btn.active')?.dataset.value || '60');
    const mood = parseInt(document.getElementById('mood-slider')?.value || '5');
    const mode = document.getElementById('decision-mode')?.value || 'smart';

    const rec = await api('/decide', {
        method: 'POST',
        body: { energy, available_minutes: time, mood, mode }
    });

    const container = document.getElementById('recommendation-result');
    container.style.display = 'block';

    if (rec.has_recommendation) {
        const name = rec.project?.name || rec.task?.name || 'Task';
        const type = rec.project ? '📁 Progetto' : '✅ Task';
        const quadrant = rec.project?.eisenhower || '';

        container.innerHTML = `
            <div class="recommendation-header">
                <div class="recommendation-type">${rec.project ? '📁' : '✅'}</div>
                <div>
                    <div class="recommendation-title">${name}</div>
                    <div class="recommendation-subtitle">${type} ${quadrant ? `• ${quadrant}` : ''}</div>
                </div>
            </div>
            <div class="recommendation-score">
                <div class="score-item">
                    <span class="score-item-value">${Math.round(rec.score)}</span>
                    <span class="score-item-label">Score</span>
                </div>
                <div class="score-item">
                    <span class="score-item-value">${Math.round(rec.confidence * 100)}%</span>
                    <span class="score-item-label">Confidence</span>
                </div>
            </div>
            <div class="recommendation-reasons-list">
                <h4>Perché questa scelta:</h4>
                <ul>
                    ${rec.reasoning.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
            ${rec.alternatives.length > 0 ? `
                <div class="recommendation-alternatives">
                    <h4>Alternative:</h4>
                    ${rec.alternatives.map(a => `
                        <div class="alternative-item">
                            <span>${a.name}</span>
                            <span>Score: ${Math.round(a.score)}</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
            <div style="margin-top: 20px;">
                <button class="btn btn-primary" onclick="startFocusOn(${rec.task?.id || 'null'}, ${rec.project?.id || 'null'}, '${name}')">
                    ▶️ Inizia Focus su questo
                </button>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>Nessun progetto o task attivo.</p>
                <button class="btn btn-primary" onclick="navigateTo('projects')">Crea un progetto</button>
            </div>
        `;
    }
}

// ==================== FOCUS MODE ====================
async function loadFocusData() {
    const today = await api('/focus/today');
    document.getElementById('focus-today-pomodoros').textContent = today.pomodoros_completed;
    document.getElementById('focus-today-minutes').textContent = today.focus_minutes;

    const status = await api('/focus/status');
    if (status.active) {
        updateFocusDisplay(status);
    }

    // Load tasks for selector
    const tasks = await api('/tasks');
    const select = document.getElementById('focus-task-select');
    select.innerHTML = '<option value="">-- Nessun task --</option>' +
        tasks.map(t => `<option value="${t.id}" data-name="${t.name}">${t.name}</option>`).join('');
}

function showFocusSetup() {
    document.getElementById('focus-setup-modal').classList.add('active');
}

function closeFocusSetup() {
    document.getElementById('focus-setup-modal').classList.remove('active');
}

async function startFocus() {
    const activeBtn = document.querySelector('.session-btn.active');
    const type = activeBtn?.dataset.type || 'pomodoro';
    const duration = parseInt(activeBtn?.dataset.duration || '25');

    const taskSelect = document.getElementById('focus-task-select');
    const taskId = taskSelect.value ? parseInt(taskSelect.value) : null;
    const taskName = taskSelect.selectedOptions[0]?.dataset.name || '';

    closeFocusSetup();

    await api('/focus/start', {
        method: 'POST',
        body: { type, duration, task_id: taskId, task_name: taskName }
    });

    focusDuration = duration * 60;
    focusStartTime = Date.now();
    focusPaused = false;

    document.getElementById('btn-start').style.display = 'none';
    document.getElementById('btn-stop').disabled = false;
    document.getElementById('btn-pause').disabled = false;
    document.getElementById('timer-interruptions').style.display = 'flex';
    document.getElementById('timer-status').textContent = 'Focus!';

    if (taskName) {
        document.getElementById('timer-task-display').style.display = 'block';
        document.getElementById('timer-task-name').textContent = taskName;
    }

    startFocusTimer();
}

function startFocusOn(taskId, projectId, name) {
    navigateTo('focus');
    setTimeout(() => {
        showFocusSetup();
        if (taskId) {
            const select = document.getElementById('focus-task-select');
            select.value = taskId;
        }
    }, 100);
}

function startFocusTimer() {
    focusInterval = setInterval(() => {
        if (focusPaused) return;

        const elapsed = Math.floor((Date.now() - focusStartTime) / 1000);
        const remaining = Math.max(0, focusDuration - elapsed);

        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;
        document.getElementById('timer-time').textContent =
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

        // Update progress circle
        const progress = (elapsed / focusDuration) * 283; // 283 = circumference
        document.getElementById('timer-progress').style.strokeDashoffset = 283 - progress;

        if (remaining <= 0) {
            completeFocus();
        }
    }, 1000);
}

async function completeFocus() {
    clearInterval(focusInterval);

    const result = await api('/focus/stop', {
        method: 'POST',
        body: { completed: true }
    });

    resetFocusUI();

    showToast(`🎉 Sessione completata! +${result.points} punti`, 'success');

    if (result.achievements?.length > 0) {
        result.achievements.forEach(a => showAchievementPopup(a));
    }

    loadProfile();
    loadFocusData();
}

async function stopFocus() {
    clearInterval(focusInterval);

    await api('/focus/stop', {
        method: 'POST',
        body: { completed: false }
    });

    resetFocusUI();
    showToast('Sessione terminata', 'info');
}

function resetFocusUI() {
    document.getElementById('btn-start').style.display = 'inline-flex';
    document.getElementById('btn-stop').disabled = true;
    document.getElementById('btn-pause').disabled = true;
    document.getElementById('timer-interruptions').style.display = 'none';
    document.getElementById('timer-task-display').style.display = 'none';
    document.getElementById('timer-time').textContent = '25:00';
    document.getElementById('timer-status').textContent = 'Pronto';
    document.getElementById('timer-progress').style.strokeDashoffset = 0;
    document.getElementById('interruption-count').textContent = '0';
}

async function togglePause() {
    if (focusPaused) {
        await api('/focus/resume', { method: 'POST' });
        focusPaused = false;
        focusStartTime = Date.now() - ((focusDuration * 1000) - (focusDuration * 1000 * (1 - parseFloat(document.getElementById('timer-progress').style.strokeDashoffset || 0) / 283)));
        document.getElementById('timer-status').textContent = 'Focus!';
        document.getElementById('btn-pause').textContent = '⏸️';
    } else {
        await api('/focus/pause', { method: 'POST' });
        focusPaused = true;
        document.getElementById('timer-status').textContent = 'In Pausa';
        document.getElementById('btn-pause').textContent = '▶️';
    }
}

async function logInterruption() {
    await api('/focus/interrupt', {
        method: 'POST',
        body: { description: '' }
    });

    const count = document.getElementById('interruption-count');
    count.textContent = parseInt(count.textContent) + 1;
}

// ==================== PROJECTS ====================
async function loadProjects() {
    const projects = await api('/projects');
    const container = document.getElementById('projects-list');

    if (projects.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📁</div>
                <p>Nessun progetto ancora. Crea il tuo primo!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = projects.map(p => `
        <div class="card project-card">
            <div class="project-header">
                <div>
                    <div class="project-name">${p.name}</div>
                </div>
                <span class="project-quadrant ${p.eisenhower}">${p.eisenhower}</span>
            </div>
            <div class="project-metrics">
                <span class="project-metric">📊 I:${p.importance}</span>
                <span class="project-metric">⏰ U:${p.urgency}</span>
                <span class="project-metric">🔥 E:${p.excitement}</span>
            </div>
            ${p.deadline ? `
                <div class="project-deadline ${p.is_overdue ? 'overdue' : ''}">
                    📅 ${p.is_overdue ? 'SCADUTO' : `${p.days_until_deadline} giorni`}
                </div>
            ` : ''}
            <div class="project-progress">
                <div class="project-progress-bar">
                    <div class="project-progress-fill" style="width: ${p.progress}%"></div>
                </div>
                <span class="project-progress-text">${Math.round(p.progress)}% completato • ${p.logged_hours}/${p.estimated_hours}h</span>
            </div>
            <div class="project-actions">
                <button class="btn btn-small btn-primary" onclick="startFocusOn(null, ${p.id}, '${p.name}')">▶️ Focus</button>
                <button class="btn btn-small btn-success" onclick="completeProject(${p.id})">✅ Completa</button>
            </div>
        </div>
    `).join('');
}

function showNewProjectModal() {
    document.getElementById('new-project-modal').classList.add('active');
}

function closeNewProjectModal() {
    document.getElementById('new-project-modal').classList.remove('active');
}

async function createProject() {
    const name = document.getElementById('project-name').value;
    if (!name) {
        showToast('Inserisci un nome per il progetto', 'error');
        return;
    }

    const project = {
        name,
        description: document.getElementById('project-description').value,
        importance: parseInt(document.getElementById('project-importance').value),
        urgency: parseInt(document.getElementById('project-urgency').value),
        excitement: parseInt(document.getElementById('project-excitement').value),
        energy_required: document.getElementById('project-energy').value,
        estimated_hours: parseInt(document.getElementById('project-hours').value),
        deadline: document.getElementById('project-deadline').value || null
    };

    await api('/projects', { method: 'POST', body: project });

    closeNewProjectModal();
    document.getElementById('project-name').value = '';
    document.getElementById('project-description').value = '';

    showToast('Progetto creato!', 'success');
    loadProjects();
    loadProfile();
}

async function completeProject(id) {
    const result = await api(`/projects/${id}/complete`, { method: 'POST' });

    showToast(`🎉 Progetto completato! +${result.points} punti`, 'success');

    if (result.achievements?.length > 0) {
        result.achievements.forEach(a => showAchievementPopup(a));
    }

    loadProjects();
    loadProfile();
}

// ==================== TASKS ====================
async function loadTasks() {
    const tasks = await api('/tasks');
    const container = document.getElementById('tasks-list');

    // Load projects for task creation
    const projects = await api('/projects');
    const projectSelect = document.getElementById('task-project');
    projectSelect.innerHTML = '<option value="">-- Nessun progetto --</option>' +
        projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');

    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <p>Nessun task. Creane uno!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = tasks.map(t => `
        <div class="task-item">
            <div class="task-checkbox" onclick="completeTask(${t.id})"></div>
            <div class="task-info">
                <div class="task-name">${t.name}</div>
                <div class="task-meta">
                    ${t.project_name ? `<span>📁 ${t.project_name}</span>` : ''}
                    <span>⏱️ ~${t.remaining_minutes} min</span>
                    <span>📊 P:${t.priority}</span>
                </div>
            </div>
            ${t.is_quick_win ? '<span class="task-badge quick-win">⚡ Quick Win</span>' : ''}
            ${t.is_micro_task ? '<span class="task-badge micro">🔬 Micro</span>' : ''}
            <div class="task-actions">
                <button class="btn btn-small btn-primary" onclick="startFocusOn(${t.id}, ${t.project_id || 'null'}, '${t.name}')">▶️</button>
                <button class="btn btn-small" onclick="splitTask(${t.id})">✂️</button>
            </div>
        </div>
    `).join('');
}

function showNewTaskModal() {
    document.getElementById('new-task-modal').classList.add('active');
}

function closeNewTaskModal() {
    document.getElementById('new-task-modal').classList.remove('active');
}

async function createTask() {
    const name = document.getElementById('task-name').value;
    if (!name) {
        showToast('Inserisci un nome per il task', 'error');
        return;
    }

    const task = {
        name,
        project_id: document.getElementById('task-project').value || null,
        estimated_minutes: parseInt(document.getElementById('task-minutes').value),
        priority: parseInt(document.getElementById('task-priority').value)
    };

    await api('/tasks', { method: 'POST', body: task });

    closeNewTaskModal();
    document.getElementById('task-name').value = '';

    showToast('Task creato!', 'success');
    loadTasks();
}

async function completeTask(id) {
    const result = await api(`/tasks/${id}/complete`, { method: 'POST' });

    showToast(`✅ Task completato! +${result.points} punti`, 'success');

    if (result.achievements?.length > 0) {
        result.achievements.forEach(a => showAchievementPopup(a));
    }

    loadTasks();
    loadProfile();
    loadTodayStats();
}

async function splitTask(id) {
    const result = await api(`/tasks/${id}/split`, { method: 'POST' });
    showToast(`✂️ Creati ${result.count} micro-task!`, 'success');
    loadTasks();
}

// ==================== ANTI-PROCRASTINATION ====================
async function loadAntiProc() {
    getMotivation();
    loadRitual();
}

async function getMotivation() {
    const data = await api('/anti-proc/motivation');
    document.getElementById('motivation-text').textContent = data.message;
}

async function loadRitual() {
    const data = await api('/anti-proc/ritual');
    const container = document.getElementById('ritual-list');
    container.innerHTML = data.steps.map(s => `<li>${s}</li>`).join('');
}

async function getIntervention(reason) {
    const data = await api('/anti-proc/intervention', {
        method: 'POST',
        body: { reason }
    });

    const card = document.getElementById('intervention-card');
    card.style.display = 'block';

    document.getElementById('intervention-technique').textContent = data.technique;
    document.getElementById('intervention-message').textContent = data.message;
    document.getElementById('intervention-action').textContent = data.action;

    card.scrollIntoView({ behavior: 'smooth' });
}

// ==================== ACHIEVEMENTS ====================
async function loadAchievements() {
    const achievements = await api('/achievements');
    const container = document.getElementById('achievements-list');

    container.innerHTML = achievements.map(a => `
        <div class="achievement-item ${a.unlocked ? 'unlocked' : 'locked'}">
            <div class="achievement-icon">${a.unlocked ? a.icon : '🔒'}</div>
            <div class="achievement-name">${a.name}</div>
            <div class="achievement-description">${a.description}</div>
            <div class="achievement-points">+${a.points} punti</div>
        </div>
    `).join('');
}

// ==================== NOTIFICATIONS ====================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function showAchievementPopup(achievement) {
    const popup = document.getElementById('achievement-popup');
    document.getElementById('achievement-popup-icon').textContent = achievement.icon;
    document.getElementById('achievement-popup-name').textContent = achievement.name;

    popup.classList.add('active');

    setTimeout(() => {
        popup.classList.remove('active');
    }, 3000);
}

// ==================== UTILITIES ====================
function updateFocusDisplay(status) {
    if (status.active) {
        document.getElementById('timer-time').textContent = status.time_remaining;
        document.getElementById('timer-status').textContent = status.paused ? 'In Pausa' : 'Focus!';
        document.getElementById('interruption-count').textContent = status.interruptions;

        if (status.task_name) {
            document.getElementById('timer-task-display').style.display = 'block';
            document.getElementById('timer-task-name').textContent = status.task_name;
        }
    }
}
