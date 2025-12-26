"""
Database manager con SQLite per persistenza dati.
Gestisce progetti, task, sessioni di focus e statistiche.
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class Database:
    """Gestisce tutte le operazioni database."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default: nella home directory dell'utente
            home = Path.home()
            app_dir = home / ".project_decision_tool"
            app_dir.mkdir(exist_ok=True)
            db_path = str(app_dir / "data.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """Inizializza tutte le tabelle del database."""
        cursor = self.conn.cursor()

        # Tabella progetti
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active',
                priority INTEGER DEFAULT 5,
                deadline TEXT,
                estimated_hours REAL DEFAULT 0,
                logged_hours REAL DEFAULT 0,
                energy_required TEXT DEFAULT 'medium',
                importance INTEGER DEFAULT 5,
                urgency INTEGER DEFAULT 5,
                excitement INTEGER DEFAULT 5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                tags TEXT DEFAULT ''
            )
        ''')

        # Tabella task
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 5,
                estimated_minutes INTEGER DEFAULT 25,
                logged_minutes INTEGER DEFAULT 0,
                energy_required TEXT DEFAULT 'medium',
                is_micro_task BOOLEAN DEFAULT 0,
                parent_task_id INTEGER,
                order_index INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                due_date TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (parent_task_id) REFERENCES tasks(id)
            )
        ''')

        # Tabella sessioni focus (Pomodoro)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                project_id INTEGER,
                duration_minutes INTEGER,
                completed BOOLEAN DEFAULT 0,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                interruptions INTEGER DEFAULT 0,
                notes TEXT,
                mood_before INTEGER,
                mood_after INTEGER,
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')

        # Tabella gamification - profilo utente
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                username TEXT DEFAULT 'User',
                total_points INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_activity_date TEXT,
                total_focus_minutes INTEGER DEFAULT 0,
                total_tasks_completed INTEGER DEFAULT 0,
                total_projects_completed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabella achievements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                points INTEGER DEFAULT 0,
                unlocked_at TEXT
            )
        ''')

        # Tabella daily stats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                focus_minutes INTEGER DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                projects_worked INTEGER DEFAULT 0,
                points_earned INTEGER DEFAULT 0,
                mood_avg REAL,
                decisions_made INTEGER DEFAULT 0
            )
        ''')

        # Tabella decisioni prese
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_type TEXT,
                chosen_project_id INTEGER,
                alternatives TEXT,
                reasoning TEXT,
                outcome TEXT,
                satisfaction INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chosen_project_id) REFERENCES projects(id)
            )
        ''')

        # Tabella blocchi/distrazioni
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS distractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                description TEXT,
                duration_seconds INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES focus_sessions(id)
            )
        ''')

        # Inizializza profilo utente se non esiste
        cursor.execute('INSERT OR IGNORE INTO user_profile (id) VALUES (1)')

        # Inizializza achievements predefiniti
        self._init_achievements(cursor)

        self.conn.commit()

    def _init_achievements(self, cursor):
        """Inizializza gli achievement predefiniti."""
        achievements = [
            ('first_task', 'Primo Passo', 'Completa il tuo primo task', '🎯', 10),
            ('first_project', 'Visionario', 'Crea il tuo primo progetto', '💡', 10),
            ('first_focus', 'Concentrato', 'Completa la prima sessione focus', '🧘', 15),
            ('streak_3', 'Costante', 'Mantieni una streak di 3 giorni', '🔥', 30),
            ('streak_7', 'Inarrestabile', 'Mantieni una streak di 7 giorni', '⚡', 75),
            ('streak_30', 'Leggenda', 'Mantieni una streak di 30 giorni', '👑', 300),
            ('tasks_10', 'Produttivo', 'Completa 10 task', '✅', 50),
            ('tasks_50', 'Macchina', 'Completa 50 task', '🚀', 150),
            ('tasks_100', 'Inesorabile', 'Completa 100 task', '💪', 300),
            ('focus_60', 'Ora di Potenza', 'Accumula 60 minuti di focus', '⏱️', 25),
            ('focus_300', 'Maratoneta', 'Accumula 5 ore di focus', '🏃', 100),
            ('focus_1000', 'Monaco Zen', 'Accumula 1000 minuti di focus', '🧠', 250),
            ('project_complete', 'Finisher', 'Completa il tuo primo progetto', '🏆', 100),
            ('no_interruptions', 'Imperturbabile', 'Completa 5 sessioni senza interruzioni', '🛡️', 75),
            ('early_bird', 'Mattiniero', 'Inizia una sessione prima delle 7', '🌅', 25),
            ('night_owl', 'Nottambulo', 'Lavora dopo mezzanotte', '🦉', 25),
            ('decision_master', 'Deciso', 'Prendi 10 decisioni con il sistema', '⚖️', 50),
            ('micro_master', 'Spacchettatore', 'Crea 20 micro-task', '🔬', 40),
            ('level_5', 'Apprendista', 'Raggiungi il livello 5', '📈', 50),
            ('level_10', 'Esperto', 'Raggiungi il livello 10', '🎓', 150),
        ]

        for code, name, desc, icon, points in achievements:
            cursor.execute('''
                INSERT OR IGNORE INTO achievements (code, name, description, icon, points)
                VALUES (?, ?, ?, ?, ?)
            ''', (code, name, desc, icon, points))

    # === PROJECT OPERATIONS ===

    def create_project(self, name: str, **kwargs) -> int:
        """Crea un nuovo progetto."""
        cursor = self.conn.cursor()

        columns = ['name']
        values = [name]

        valid_fields = ['description', 'priority', 'deadline', 'estimated_hours',
                       'energy_required', 'importance', 'urgency', 'excitement', 'tags']

        for field in valid_fields:
            if field in kwargs:
                columns.append(field)
                values.append(kwargs[field])

        placeholders = ', '.join(['?' for _ in values])
        columns_str = ', '.join(columns)

        cursor.execute(f'''
            INSERT INTO projects ({columns_str}) VALUES ({placeholders})
        ''', values)

        self.conn.commit()
        return cursor.lastrowid

    def get_project(self, project_id: int) -> Optional[Dict]:
        """Ottiene un progetto per ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_projects(self, status: str = None) -> List[Dict]:
        """Ottiene tutti i progetti, opzionalmente filtrati per status."""
        cursor = self.conn.cursor()
        if status:
            cursor.execute('SELECT * FROM projects WHERE status = ? ORDER BY priority DESC', (status,))
        else:
            cursor.execute('SELECT * FROM projects ORDER BY priority DESC')
        return [dict(row) for row in cursor.fetchall()]

    def update_project(self, project_id: int, **kwargs) -> bool:
        """Aggiorna un progetto."""
        if not kwargs:
            return False

        cursor = self.conn.cursor()
        kwargs['updated_at'] = datetime.now().isoformat()

        set_clause = ', '.join([f'{k} = ?' for k in kwargs.keys()])
        values = list(kwargs.values()) + [project_id]

        cursor.execute(f'UPDATE projects SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_project(self, project_id: int) -> bool:
        """Elimina un progetto e i suoi task."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE project_id = ?', (project_id,))
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # === TASK OPERATIONS ===

    def create_task(self, name: str, project_id: int = None, **kwargs) -> int:
        """Crea un nuovo task."""
        cursor = self.conn.cursor()

        columns = ['name']
        values = [name]

        if project_id:
            columns.append('project_id')
            values.append(project_id)

        valid_fields = ['description', 'priority', 'estimated_minutes', 'energy_required',
                       'is_micro_task', 'parent_task_id', 'order_index', 'due_date']

        for field in valid_fields:
            if field in kwargs:
                columns.append(field)
                values.append(kwargs[field])

        placeholders = ', '.join(['?' for _ in values])
        columns_str = ', '.join(columns)

        cursor.execute(f'INSERT INTO tasks ({columns_str}) VALUES ({placeholders})', values)
        self.conn.commit()
        return cursor.lastrowid

    def get_task(self, task_id: int) -> Optional[Dict]:
        """Ottiene un task per ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_tasks(self, project_id: int = None, status: str = None,
                  parent_task_id: int = None) -> List[Dict]:
        """Ottiene task con filtri opzionali."""
        cursor = self.conn.cursor()

        query = 'SELECT * FROM tasks WHERE 1=1'
        params = []

        if project_id:
            query += ' AND project_id = ?'
            params.append(project_id)
        if status:
            query += ' AND status = ?'
            params.append(status)
        if parent_task_id is not None:
            query += ' AND parent_task_id = ?'
            params.append(parent_task_id)

        query += ' ORDER BY priority DESC, order_index ASC'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_pending_tasks(self, limit: int = None) -> List[Dict]:
        """Ottiene i task pending ordinati per priorità."""
        cursor = self.conn.cursor()
        query = '''
            SELECT t.*, p.name as project_name
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.status = 'pending'
            ORDER BY t.priority DESC, t.created_at ASC
        '''
        if limit:
            query += f' LIMIT {limit}'
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def update_task(self, task_id: int, **kwargs) -> bool:
        """Aggiorna un task."""
        if not kwargs:
            return False

        cursor = self.conn.cursor()
        set_clause = ', '.join([f'{k} = ?' for k in kwargs.keys()])
        values = list(kwargs.values()) + [task_id]

        cursor.execute(f'UPDATE tasks SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        return cursor.rowcount > 0

    def complete_task(self, task_id: int) -> bool:
        """Segna un task come completato."""
        return self.update_task(task_id,
                               status='completed',
                               completed_at=datetime.now().isoformat())

    def get_micro_tasks(self, parent_task_id: int) -> List[Dict]:
        """Ottiene i micro-task di un task padre."""
        return self.get_tasks(parent_task_id=parent_task_id)

    # === FOCUS SESSION OPERATIONS ===

    def create_focus_session(self, duration_minutes: int,
                            task_id: int = None, project_id: int = None,
                            mood_before: int = None) -> int:
        """Crea una nuova sessione focus."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO focus_sessions (duration_minutes, task_id, project_id, mood_before)
            VALUES (?, ?, ?, ?)
        ''', (duration_minutes, task_id, project_id, mood_before))
        self.conn.commit()
        return cursor.lastrowid

    def end_focus_session(self, session_id: int, completed: bool = True,
                         interruptions: int = 0, mood_after: int = None,
                         notes: str = None) -> bool:
        """Termina una sessione focus."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE focus_sessions
            SET completed = ?, ended_at = ?, interruptions = ?, mood_after = ?, notes = ?
            WHERE id = ?
        ''', (completed, datetime.now().isoformat(), interruptions, mood_after, notes, session_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_focus_sessions(self, date: str = None, limit: int = None) -> List[Dict]:
        """Ottiene le sessioni focus."""
        cursor = self.conn.cursor()
        query = 'SELECT * FROM focus_sessions'
        params = []

        if date:
            query += ' WHERE DATE(started_at) = ?'
            params.append(date)

        query += ' ORDER BY started_at DESC'

        if limit:
            query += f' LIMIT {limit}'

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # === USER PROFILE OPERATIONS ===

    def get_user_profile(self) -> Dict:
        """Ottiene il profilo utente."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM user_profile WHERE id = 1')
        row = cursor.fetchone()
        return dict(row) if row else {}

    def update_user_profile(self, **kwargs) -> bool:
        """Aggiorna il profilo utente."""
        if not kwargs:
            return False

        cursor = self.conn.cursor()
        set_clause = ', '.join([f'{k} = ?' for k in kwargs.keys()])
        values = list(kwargs.values())

        cursor.execute(f'UPDATE user_profile SET {set_clause} WHERE id = 1', values)
        self.conn.commit()
        return cursor.rowcount > 0

    def add_points(self, points: int) -> int:
        """Aggiunge punti all'utente e ritorna il totale."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE user_profile
            SET total_points = total_points + ?
            WHERE id = 1
        ''', (points,))
        self.conn.commit()

        cursor.execute('SELECT total_points FROM user_profile WHERE id = 1')
        return cursor.fetchone()[0]

    # === ACHIEVEMENTS ===

    def get_achievements(self, unlocked_only: bool = False) -> List[Dict]:
        """Ottiene gli achievement."""
        cursor = self.conn.cursor()
        if unlocked_only:
            cursor.execute('SELECT * FROM achievements WHERE unlocked_at IS NOT NULL')
        else:
            cursor.execute('SELECT * FROM achievements')
        return [dict(row) for row in cursor.fetchall()]

    def unlock_achievement(self, code: str) -> Optional[Dict]:
        """Sblocca un achievement e ritorna i suoi dettagli."""
        cursor = self.conn.cursor()

        # Check if already unlocked
        cursor.execute('SELECT * FROM achievements WHERE code = ?', (code,))
        achievement = cursor.fetchone()

        if not achievement or achievement['unlocked_at']:
            return None

        cursor.execute('''
            UPDATE achievements SET unlocked_at = ? WHERE code = ?
        ''', (datetime.now().isoformat(), code))

        self.conn.commit()
        return dict(achievement)

    # === DAILY STATS ===

    def get_or_create_daily_stats(self, date: str = None) -> Dict:
        """Ottiene o crea le statistiche giornaliere."""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (date,))
        row = cursor.fetchone()

        if row:
            return dict(row)

        cursor.execute('INSERT INTO daily_stats (date) VALUES (?)', (date,))
        self.conn.commit()

        cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (date,))
        return dict(cursor.fetchone())

    def update_daily_stats(self, date: str = None, **kwargs) -> bool:
        """Aggiorna le statistiche giornaliere."""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # Assicurati che il record esista
        self.get_or_create_daily_stats(date)

        if not kwargs:
            return False

        cursor = self.conn.cursor()
        set_clause = ', '.join([f'{k} = {k} + ?' if k != 'mood_avg' else f'{k} = ?'
                               for k in kwargs.keys()])
        values = list(kwargs.values()) + [date]

        cursor.execute(f'UPDATE daily_stats SET {set_clause} WHERE date = ?', values)
        self.conn.commit()
        return cursor.rowcount > 0

    def get_stats_range(self, days: int = 7) -> List[Dict]:
        """Ottiene le statistiche degli ultimi N giorni."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM daily_stats
            ORDER BY date DESC
            LIMIT ?
        ''', (days,))
        return [dict(row) for row in cursor.fetchall()]

    # === DECISIONS ===

    def log_decision(self, decision_type: str, chosen_project_id: int,
                    alternatives: str = None, reasoning: str = None) -> int:
        """Registra una decisione presa."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO decisions (decision_type, chosen_project_id, alternatives, reasoning)
            VALUES (?, ?, ?, ?)
        ''', (decision_type, chosen_project_id, alternatives, reasoning))
        self.conn.commit()

        # Aggiorna statistiche giornaliere
        self.update_daily_stats(decisions_made=1)

        return cursor.lastrowid

    # === DISTRACTIONS ===

    def log_distraction(self, session_id: int, description: str,
                       duration_seconds: int = 0) -> int:
        """Registra una distrazione durante una sessione."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO distractions (session_id, description, duration_seconds)
            VALUES (?, ?, ?)
        ''', (session_id, description, duration_seconds))

        # Incrementa contatore interruzioni nella sessione
        cursor.execute('''
            UPDATE focus_sessions SET interruptions = interruptions + 1 WHERE id = ?
        ''', (session_id,))

        self.conn.commit()
        return cursor.lastrowid

    def close(self):
        """Chiude la connessione al database."""
        self.conn.close()
