#!/usr/bin/env python3
"""
Project Decision Tool - Web App
Server Flask con API REST e interfaccia grafica.
"""

import sys
import os
from datetime import datetime

# Aggiungi parent directory per imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request
from core.database import Database
from core.project import Project, ProjectStatus, EnergyLevel
from core.task import Task, TaskStatus, TaskSuggestion
from core.decision_engine import DecisionEngine, DecisionMode, DecisionContext
from core.focus_mode import FocusMode, SessionType
from core.gamification import GamificationSystem
from core.anti_procrastination import AntiProcrastination, ProcrastinationReason
from core.analytics import Analytics

app = Flask(__name__)

# Inizializza componenti
db = Database()
decision_engine = DecisionEngine(db)
focus_mode = FocusMode(db)
gamification = GamificationSystem(db)
anti_proc = AntiProcrastination(db)
analytics = Analytics(db)


# ==================== PAGES ====================

@app.route('/')
def index():
    """Pagina principale - Dashboard."""
    return render_template('index.html')


# ==================== API: PROFILE ====================

@app.route('/api/profile')
def get_profile():
    """Ottiene il profilo utente."""
    profile = gamification.get_profile()
    streak, _, _ = gamification.update_streak()

    return jsonify({
        'username': profile.get('username', 'User'),
        'level': profile['level_info'].level,
        'level_name': profile['level_info'].name,
        'level_icon': profile['level_info'].icon,
        'total_points': profile['total_points'],
        'level_progress': profile['level_progress'],
        'points_to_next': profile['points_to_next_level'],
        'streak': profile['current_streak'],
        'longest_streak': profile.get('longest_streak', 0),
        'streak_multiplier': profile['streak_multiplier'],
        'total_tasks': profile.get('total_tasks_completed', 0),
        'total_focus_minutes': profile.get('total_focus_minutes', 0),
        'total_projects': profile.get('total_projects_completed', 0)
    })


# ==================== API: STATS ====================

@app.route('/api/stats/today')
def get_today_stats():
    """Statistiche di oggi."""
    summary = analytics.get_daily_summary()
    return jsonify(summary)


@app.route('/api/stats/weekly')
def get_weekly_stats():
    """Statistiche settimanali."""
    summary = analytics.get_weekly_summary()
    # Converti per JSON
    if 'daily_breakdown' in summary:
        summary['daily_breakdown'] = [dict(d) for d in summary['daily_breakdown']]
    return jsonify(summary)


@app.route('/api/stats/score')
def get_productivity_score():
    """Productivity score."""
    score, description = analytics.get_productivity_score()
    return jsonify({
        'score': score,
        'description': description
    })


@app.route('/api/insights')
def get_insights():
    """Ottiene insights."""
    insights = analytics.get_insights()
    return jsonify(insights)


@app.route('/api/challenges')
def get_challenges():
    """Sfide giornaliere."""
    challenges = gamification.get_daily_challenges()
    return jsonify(challenges)


# ==================== API: PROJECTS ====================

@app.route('/api/projects')
def get_projects():
    """Lista tutti i progetti."""
    status = request.args.get('status', 'active')
    raw_projects = db.get_all_projects(status if status != 'all' else None)

    projects = []
    for p in raw_projects:
        proj = Project.from_dict(p)
        projects.append({
            'id': p['id'],
            'name': p['name'],
            'description': p.get('description', ''),
            'status': p['status'],
            'priority': p['priority'],
            'importance': p['importance'],
            'urgency': p['urgency'],
            'excitement': p['excitement'],
            'energy_required': p['energy_required'],
            'progress': proj.progress,
            'eisenhower': proj.eisenhower_quadrant,
            'deadline': p.get('deadline'),
            'days_until_deadline': proj.days_until_deadline,
            'is_overdue': proj.is_overdue,
            'estimated_hours': p.get('estimated_hours', 0),
            'logged_hours': p.get('logged_hours', 0)
        })

    return jsonify(projects)


@app.route('/api/projects', methods=['POST'])
def create_project():
    """Crea un nuovo progetto."""
    data = request.json

    project_id = db.create_project(
        name=data['name'],
        description=data.get('description', ''),
        importance=data.get('importance', 5),
        urgency=data.get('urgency', 5),
        excitement=data.get('excitement', 5),
        energy_required=data.get('energy_required', 'medium'),
        estimated_hours=data.get('estimated_hours', 10),
        deadline=data.get('deadline')
    )

    # Punti per decisione
    gamification.award_points('decision_made')

    return jsonify({'id': project_id, 'success': True})


@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Aggiorna un progetto."""
    data = request.json
    db.update_project(project_id, **data)
    return jsonify({'success': True})


@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Elimina un progetto."""
    db.delete_project(project_id)
    return jsonify({'success': True})


@app.route('/api/projects/<int:project_id>/complete', methods=['POST'])
def complete_project(project_id):
    """Completa un progetto."""
    db.update_project(project_id, status='completed',
                     completed_at=datetime.now().isoformat())

    project = db.get_project(project_id)
    points, achievements = gamification.on_project_completed(project)

    return jsonify({
        'success': True,
        'points': points,
        'achievements': [{'name': a.name, 'icon': a.icon} for a in achievements]
    })


# ==================== API: TASKS ====================

@app.route('/api/tasks')
def get_tasks():
    """Lista task."""
    status = request.args.get('status', 'pending')
    project_id = request.args.get('project_id')

    if project_id:
        raw_tasks = db.get_tasks(project_id=int(project_id), status=status)
    else:
        raw_tasks = db.get_pending_tasks(limit=50) if status == 'pending' else db.get_tasks(status=status)

    tasks = []
    for t in raw_tasks:
        task = Task.from_dict(t)
        tasks.append({
            'id': t['id'],
            'name': t['name'],
            'description': t.get('description', ''),
            'project_id': t.get('project_id'),
            'project_name': t.get('project_name', ''),
            'status': t['status'],
            'priority': t['priority'],
            'estimated_minutes': t['estimated_minutes'],
            'logged_minutes': t.get('logged_minutes', 0),
            'remaining_minutes': task.remaining_minutes,
            'progress': task.progress,
            'is_micro_task': t.get('is_micro_task', False),
            'is_quick_win': task.is_quick_win,
            'energy_required': t.get('energy_required', 'medium')
        })

    return jsonify(tasks)


@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Crea un nuovo task."""
    data = request.json

    task_id = db.create_task(
        name=data['name'],
        project_id=data.get('project_id'),
        description=data.get('description', ''),
        priority=data.get('priority', 5),
        estimated_minutes=data.get('estimated_minutes', 25),
        energy_required=data.get('energy_required', 'medium')
    )

    return jsonify({'id': task_id, 'success': True})


@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Completa un task."""
    db.complete_task(task_id)
    db.update_daily_stats(tasks_completed=1)

    task = db.get_task(task_id)
    points, achievements = gamification.on_task_completed(task)

    return jsonify({
        'success': True,
        'points': points,
        'achievements': [{'name': a.name, 'icon': a.icon} for a in achievements]
    })


@app.route('/api/tasks/<int:task_id>/split', methods=['POST'])
def split_task(task_id):
    """Spacchetta un task in micro-task."""
    task_data = db.get_task(task_id)
    if not task_data:
        return jsonify({'error': 'Task not found'}), 404

    task = Task.from_dict(task_data)
    task_ids = anti_proc.create_micro_tasks_in_db(task)

    return jsonify({
        'success': True,
        'micro_task_ids': task_ids,
        'count': len(task_ids)
    })


# ==================== API: DECISION ENGINE ====================

@app.route('/api/decide', methods=['POST'])
def get_decision():
    """Ottiene una raccomandazione."""
    data = request.json or {}

    # Costruisci contesto
    energy_map = {
        'low': EnergyLevel.LOW,
        'medium': EnergyLevel.MEDIUM,
        'high': EnergyLevel.HIGH,
        'extreme': EnergyLevel.EXTREME
    }

    context = DecisionContext(
        current_energy=energy_map.get(data.get('energy', 'medium'), EnergyLevel.MEDIUM),
        available_minutes=data.get('available_minutes', 60),
        mood=data.get('mood', 5)
    )

    mode_map = {
        'smart': DecisionMode.SMART,
        'urgent': DecisionMode.URGENT,
        'energy': DecisionMode.ENERGY_MATCH,
        'quick': DecisionMode.QUICK_WINS,
        'random': DecisionMode.RANDOM_TOP3
    }
    mode = mode_map.get(data.get('mode', 'smart'), DecisionMode.SMART)

    rec = decision_engine.get_recommendation(context, mode)

    result = {
        'has_recommendation': rec.project is not None or rec.task is not None,
        'project': None,
        'task': None,
        'score': rec.score,
        'confidence': rec.confidence,
        'reasoning': rec.reasoning,
        'alternatives': []
    }

    if rec.project:
        result['project'] = {
            'id': rec.project.id,
            'name': rec.project.name,
            'importance': rec.project.importance,
            'urgency': rec.project.urgency,
            'eisenhower': rec.project.eisenhower_quadrant
        }

    if rec.task:
        result['task'] = {
            'id': rec.task.id,
            'name': rec.task.name,
            'remaining_minutes': rec.task.remaining_minutes
        }

    for alt in rec.alternatives[:3]:
        alt_data = {'score': alt.score}
        if alt.project:
            alt_data['name'] = alt.project.name
            alt_data['type'] = 'project'
        elif alt.task:
            alt_data['name'] = alt.task.name
            alt_data['type'] = 'task'
        result['alternatives'].append(alt_data)

    return jsonify(result)


@app.route('/api/daily-plan')
def get_daily_plan():
    """Piano giornaliero."""
    plan = decision_engine.get_daily_focus_suggestion()

    result = {
        'star_project': None,
        'quick_wins': [],
        'main_task': None,
        'total_tasks': plan['total_tasks'],
        'total_projects': plan['total_projects']
    }

    if plan['star_project']:
        result['star_project'] = {
            'id': plan['star_project'].id,
            'name': plan['star_project'].name,
            'importance': plan['star_project'].importance
        }

    for qw in plan['quick_wins']:
        result['quick_wins'].append({
            'id': qw.id,
            'name': qw.name,
            'minutes': qw.remaining_minutes
        })

    if plan['main_task']:
        result['main_task'] = {
            'id': plan['main_task'].id,
            'name': plan['main_task'].name
        }

    return jsonify(result)


# ==================== API: FOCUS MODE ====================

@app.route('/api/focus/status')
def get_focus_status():
    """Stato sessione focus."""
    return jsonify(focus_mode.get_session_status())


@app.route('/api/focus/start', methods=['POST'])
def start_focus():
    """Inizia sessione focus."""
    data = request.json or {}

    session_type_map = {
        'pomodoro': SessionType.POMODORO,
        'short': SessionType.SHORT,
        'long': SessionType.LONG,
        'break_short': SessionType.BREAK_SHORT,
        'break_long': SessionType.BREAK_LONG
    }

    session = focus_mode.start_session(
        session_type=session_type_map.get(data.get('type', 'pomodoro'), SessionType.POMODORO),
        duration_minutes=data.get('duration'),
        task_id=data.get('task_id'),
        project_id=data.get('project_id'),
        task_name=data.get('task_name', ''),
        project_name=data.get('project_name', ''),
        mood_before=data.get('mood_before')
    )

    return jsonify({
        'success': True,
        'session_id': session.id,
        'duration': session.duration_minutes
    })


@app.route('/api/focus/stop', methods=['POST'])
def stop_focus():
    """Ferma sessione focus."""
    data = request.json or {}

    session = focus_mode.stop_session(
        completed=data.get('completed', False),
        mood_after=data.get('mood_after')
    )

    if session and data.get('completed'):
        action = 'pomodoro_no_interruptions' if session.interruptions == 0 else 'pomodoro_completed'
        points, achievements = gamification.award_points(action)
        return jsonify({
            'success': True,
            'points': points,
            'achievements': [{'name': a.name, 'icon': a.icon} for a in achievements]
        })

    return jsonify({'success': True})


@app.route('/api/focus/pause', methods=['POST'])
def pause_focus():
    """Pausa sessione."""
    focus_mode.pause_session()
    return jsonify({'success': True})


@app.route('/api/focus/resume', methods=['POST'])
def resume_focus():
    """Riprendi sessione."""
    focus_mode.resume_session()
    return jsonify({'success': True})


@app.route('/api/focus/interrupt', methods=['POST'])
def log_interruption():
    """Registra interruzione."""
    data = request.json or {}
    focus_mode.log_interruption(data.get('description', ''))
    return jsonify({'success': True})


@app.route('/api/focus/today')
def get_focus_today():
    """Sommario focus oggi."""
    return jsonify(focus_mode.get_today_summary())


# ==================== API: ANTI-PROCRASTINATION ====================

@app.route('/api/anti-proc/intervention', methods=['POST'])
def get_intervention():
    """Ottiene un intervento anti-procrastinazione."""
    data = request.json or {}

    reason_map = {
        'too_big': ProcrastinationReason.TOO_BIG,
        'unclear': ProcrastinationReason.UNCLEAR,
        'boring': ProcrastinationReason.BORING,
        'scary': ProcrastinationReason.SCARY,
        'perfectionism': ProcrastinationReason.PERFECTIONISM,
        'low_energy': ProcrastinationReason.LOW_ENERGY,
        'overwhelmed': ProcrastinationReason.OVERWHELMED
    }

    reason = reason_map.get(data.get('reason'), None)
    intervention = anti_proc.get_intervention(reason)

    return jsonify({
        'technique': intervention.technique,
        'action': intervention.action,
        'message': intervention.message
    })


@app.route('/api/anti-proc/motivation')
def get_motivation():
    """Messaggio motivazionale."""
    return jsonify({
        'message': anti_proc.get_motivation_message()
    })


@app.route('/api/anti-proc/ritual')
def get_ritual():
    """Rituale di avvio."""
    return jsonify({
        'steps': anti_proc.get_startup_ritual()
    })


# ==================== API: ACHIEVEMENTS ====================

@app.route('/api/achievements')
def get_achievements():
    """Lista achievements."""
    achievements = gamification.get_all_achievements()
    return jsonify([{
        'code': a.code,
        'name': a.name,
        'description': a.description,
        'icon': a.icon,
        'points': a.points,
        'unlocked': a.unlocked,
        'unlocked_at': a.unlocked_at.isoformat() if a.unlocked_at else None
    } for a in achievements])


# ==================== MAIN ====================

if __name__ == '__main__':
    print("\n🎯 Project Decision Tool - Web App")
    print("=" * 40)
    print("Apri http://localhost:5000 nel browser")
    print("=" * 40 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
