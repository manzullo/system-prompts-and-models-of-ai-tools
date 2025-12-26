"""
Gamification System - Punti, streak, livelli, achievements.
Rende la produttività un gioco!
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .database import Database


@dataclass
class LevelInfo:
    """Informazioni su un livello."""
    level: int
    name: str
    min_points: int
    max_points: int
    icon: str


@dataclass
class Achievement:
    """Un achievement sbloccato o da sbloccare."""
    code: str
    name: str
    description: str
    icon: str
    points: int
    unlocked: bool
    unlocked_at: Optional[datetime] = None


class GamificationSystem:
    """
    Sistema di gamification per rendere la produttività coinvolgente.
    Include: punti, livelli, streak, achievements.
    """

    # Definizione livelli
    LEVELS = [
        LevelInfo(1, "Novizio", 0, 99, "🌱"),
        LevelInfo(2, "Apprendista", 100, 299, "📚"),
        LevelInfo(3, "Praticante", 300, 599, "⚒️"),
        LevelInfo(4, "Artigiano", 600, 999, "🔧"),
        LevelInfo(5, "Esperto", 1000, 1499, "🎯"),
        LevelInfo(6, "Maestro", 1500, 2499, "🎓"),
        LevelInfo(7, "Gran Maestro", 2500, 3999, "👑"),
        LevelInfo(8, "Leggenda", 4000, 5999, "⭐"),
        LevelInfo(9, "Mito", 6000, 9999, "🌟"),
        LevelInfo(10, "Illuminato", 10000, float('inf'), "💫"),
    ]

    # Punti per azioni
    POINTS = {
        'task_completed': 10,
        'micro_task_completed': 5,
        'pomodoro_completed': 15,
        'pomodoro_no_interruptions': 25,
        'project_completed': 100,
        'streak_maintained': 20,
        'quick_win': 8,
        'morning_session': 5,  # Bonus mattiniero
        'night_session': 5,    # Bonus nottambulo
        'decision_made': 3,
    }

    # Moltiplicatori streak
    STREAK_MULTIPLIERS = {
        3: 1.1,   # 3 giorni: +10%
        7: 1.25,  # 7 giorni: +25%
        14: 1.5,  # 14 giorni: +50%
        30: 2.0,  # 30 giorni: x2!
    }

    def __init__(self, db: Database):
        self.db = db
        self._cached_profile = None
        self._load_profile()

    def _load_profile(self):
        """Carica il profilo utente."""
        self._cached_profile = self.db.get_user_profile()

    def get_profile(self) -> Dict:
        """Ritorna il profilo utente completo."""
        profile = self.db.get_user_profile()
        level = self.get_level_info(profile['total_points'])

        # Calcola progressione verso prossimo livello
        points_in_level = profile['total_points'] - level.min_points
        points_needed = level.max_points - level.min_points
        level_progress = (points_in_level / points_needed * 100) if points_needed > 0 else 100

        return {
            **profile,
            'level_info': level,
            'level_progress': min(100, level_progress),
            'points_to_next_level': max(0, level.max_points - profile['total_points']),
            'streak_multiplier': self.get_streak_multiplier(profile['current_streak'])
        }

    def get_level_info(self, total_points: int) -> LevelInfo:
        """Determina il livello basato sui punti."""
        for level in self.LEVELS:
            if level.min_points <= total_points <= level.max_points:
                return level
        return self.LEVELS[-1]  # Max level

    def get_streak_multiplier(self, streak_days: int) -> float:
        """Calcola il moltiplicatore streak."""
        multiplier = 1.0
        for days, mult in sorted(self.STREAK_MULTIPLIERS.items()):
            if streak_days >= days:
                multiplier = mult
        return multiplier

    def award_points(self, action: str, base_points: int = None,
                    description: str = None) -> Tuple[int, List[Achievement]]:
        """
        Assegna punti per un'azione.
        Ritorna (punti_assegnati, [achievements_sbloccati]).
        """
        if base_points is None:
            base_points = self.POINTS.get(action, 0)

        if base_points <= 0:
            return 0, []

        # Applica moltiplicatore streak
        profile = self.db.get_user_profile()
        multiplier = self.get_streak_multiplier(profile['current_streak'])
        final_points = int(base_points * multiplier)

        # Aggiorna punti nel database
        new_total = self.db.add_points(final_points)

        # Aggiorna stats giornaliere
        self.db.update_daily_stats(points_earned=final_points)

        # Check per nuovi achievements
        unlocked = self._check_achievements(action, new_total, profile)

        # Aggiorna livello se necessario
        old_level = self.get_level_info(profile['total_points'])
        new_level = self.get_level_info(new_total)

        if new_level.level > old_level.level:
            self.db.update_user_profile(level=new_level.level)
            # Achievement per livello?
            if new_level.level >= 5:
                lvl_achievement = self._try_unlock_achievement('level_5')
                if lvl_achievement:
                    unlocked.append(lvl_achievement)
            if new_level.level >= 10:
                lvl_achievement = self._try_unlock_achievement('level_10')
                if lvl_achievement:
                    unlocked.append(lvl_achievement)

        return final_points, unlocked

    def update_streak(self) -> Tuple[int, bool, List[Achievement]]:
        """
        Aggiorna la streak giornaliera.
        Ritorna (streak_attuale, streak_aumentata, [achievements]).
        """
        profile = self.db.get_user_profile()
        today = datetime.now().strftime('%Y-%m-%d')
        last_activity = profile.get('last_activity_date')

        unlocked = []
        streak_increased = False

        if last_activity == today:
            # Già aggiornato oggi
            return profile['current_streak'], False, []

        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        if last_activity == yesterday:
            # Streak continua!
            new_streak = profile['current_streak'] + 1
            streak_increased = True
        elif last_activity is None:
            # Prima attività
            new_streak = 1
            streak_increased = True
        else:
            # Streak persa 😢
            new_streak = 1

        # Aggiorna database
        longest = max(profile.get('longest_streak', 0), new_streak)
        self.db.update_user_profile(
            current_streak=new_streak,
            longest_streak=longest,
            last_activity_date=today
        )

        # Check achievements streak
        if new_streak >= 3:
            ach = self._try_unlock_achievement('streak_3')
            if ach:
                unlocked.append(ach)
        if new_streak >= 7:
            ach = self._try_unlock_achievement('streak_7')
            if ach:
                unlocked.append(ach)
        if new_streak >= 30:
            ach = self._try_unlock_achievement('streak_30')
            if ach:
                unlocked.append(ach)

        # Punti streak
        if streak_increased and new_streak > 1:
            points, _ = self.award_points('streak_maintained')

        return new_streak, streak_increased, unlocked

    def _check_achievements(self, action: str, total_points: int,
                           profile: Dict) -> List[Achievement]:
        """Verifica e sblocca achievements basati sull'azione."""
        unlocked = []

        # Achievement per prima azione
        if action == 'task_completed':
            ach = self._try_unlock_achievement('first_task')
            if ach:
                unlocked.append(ach)

            # Contatore tasks
            tasks_completed = profile.get('total_tasks_completed', 0) + 1
            self.db.update_user_profile(total_tasks_completed=tasks_completed)

            if tasks_completed >= 10:
                ach = self._try_unlock_achievement('tasks_10')
                if ach:
                    unlocked.append(ach)
            if tasks_completed >= 50:
                ach = self._try_unlock_achievement('tasks_50')
                if ach:
                    unlocked.append(ach)
            if tasks_completed >= 100:
                ach = self._try_unlock_achievement('tasks_100')
                if ach:
                    unlocked.append(ach)

        elif action == 'pomodoro_completed':
            ach = self._try_unlock_achievement('first_focus')
            if ach:
                unlocked.append(ach)

            # Minuti di focus
            focus_minutes = profile.get('total_focus_minutes', 0) + 25
            self.db.update_user_profile(total_focus_minutes=focus_minutes)

            if focus_minutes >= 60:
                ach = self._try_unlock_achievement('focus_60')
                if ach:
                    unlocked.append(ach)
            if focus_minutes >= 300:
                ach = self._try_unlock_achievement('focus_300')
                if ach:
                    unlocked.append(ach)
            if focus_minutes >= 1000:
                ach = self._try_unlock_achievement('focus_1000')
                if ach:
                    unlocked.append(ach)

        elif action == 'pomodoro_no_interruptions':
            # Conta sessioni senza interruzioni
            # Semplificato: ogni 5 trigger l'achievement
            ach = self._try_unlock_achievement('no_interruptions')
            if ach:
                unlocked.append(ach)

        elif action == 'project_completed':
            ach = self._try_unlock_achievement('project_complete')
            if ach:
                unlocked.append(ach)

            projects_completed = profile.get('total_projects_completed', 0) + 1
            self.db.update_user_profile(total_projects_completed=projects_completed)

        elif action == 'decision_made':
            # Semplificato
            ach = self._try_unlock_achievement('decision_master')
            if ach:
                unlocked.append(ach)

        return unlocked

    def _try_unlock_achievement(self, code: str) -> Optional[Achievement]:
        """Prova a sbloccare un achievement, ritorna None se già sbloccato."""
        result = self.db.unlock_achievement(code)
        if result:
            # Aggiungi i punti dell'achievement
            self.db.add_points(result['points'])
            return Achievement(
                code=result['code'],
                name=result['name'],
                description=result['description'],
                icon=result['icon'],
                points=result['points'],
                unlocked=True,
                unlocked_at=datetime.now()
            )
        return None

    def on_task_completed(self, task_dict: Dict) -> Tuple[int, List[Achievement]]:
        """Handler per task completato."""
        action = 'micro_task_completed' if task_dict.get('is_micro_task') else 'task_completed'
        return self.award_points(action)

    def on_focus_session_completed(self, session_dict: Dict) -> Tuple[int, List[Achievement]]:
        """Handler per sessione focus completata."""
        if session_dict.get('interruptions', 0) == 0:
            action = 'pomodoro_no_interruptions'
        else:
            action = 'pomodoro_completed'
        return self.award_points(action)

    def on_project_completed(self, project_dict: Dict) -> Tuple[int, List[Achievement]]:
        """Handler per progetto completato."""
        return self.award_points('project_completed')

    def get_all_achievements(self) -> List[Achievement]:
        """Ritorna tutti gli achievements con stato di sblocco."""
        raw = self.db.get_achievements()
        return [
            Achievement(
                code=a['code'],
                name=a['name'],
                description=a['description'],
                icon=a['icon'],
                points=a['points'],
                unlocked=a['unlocked_at'] is not None,
                unlocked_at=datetime.fromisoformat(a['unlocked_at']) if a['unlocked_at'] else None
            )
            for a in raw
        ]

    def get_unlocked_achievements(self) -> List[Achievement]:
        """Ritorna solo gli achievements sbloccati."""
        return [a for a in self.get_all_achievements() if a.unlocked]

    def get_daily_challenges(self) -> List[Dict]:
        """
        Genera sfide giornaliere per mantenere engagement.
        """
        profile = self.db.get_user_profile()
        today_stats = self.db.get_or_create_daily_stats()

        challenges = []

        # Sfida focus
        focus_goal = 60 if profile['level'] < 5 else 120
        focus_done = today_stats.get('focus_minutes', 0)
        challenges.append({
            'name': 'Focus Time',
            'description': f'Accumula {focus_goal} minuti di focus oggi',
            'progress': min(100, focus_done / focus_goal * 100),
            'current': focus_done,
            'goal': focus_goal,
            'reward': 50,
            'completed': focus_done >= focus_goal,
            'icon': '🧘'
        })

        # Sfida tasks
        tasks_goal = 3 if profile['level'] < 5 else 5
        tasks_done = today_stats.get('tasks_completed', 0)
        challenges.append({
            'name': 'Task Crusher',
            'description': f'Completa {tasks_goal} task oggi',
            'progress': min(100, tasks_done / tasks_goal * 100),
            'current': tasks_done,
            'goal': tasks_goal,
            'reward': 40,
            'completed': tasks_done >= tasks_goal,
            'icon': '✅'
        })

        # Sfida streak
        streak = profile.get('current_streak', 0)
        challenges.append({
            'name': 'Streak Keeper',
            'description': 'Mantieni la tua streak oggi!',
            'progress': 100 if streak > 0 else 0,
            'current': streak,
            'goal': 1,
            'reward': 20,
            'completed': streak > 0,
            'icon': '🔥'
        })

        return challenges

    def generate_stats_display(self) -> str:
        """Genera display ASCII delle statistiche."""
        profile = self.get_profile()
        level = profile['level_info']

        lines = [
            "╔═══════════════════════════════════════════╗",
            f"║  {level.icon} {profile.get('username', 'User'):<25} Lv.{level.level:>3}  ║",
            "╠═══════════════════════════════════════════╣",
            f"║  Punti totali: {profile['total_points']:>25,}  ║",
            f"║  Livello: {level.name:>31}  ║",
        ]

        # Progress bar livello
        progress = profile['level_progress']
        bar_width = 20
        filled = int(bar_width * progress / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        lines.append(f"║  Progresso: [{bar}] {progress:>5.1f}%  ║")

        # Streak
        streak = profile['current_streak']
        streak_display = f"🔥 {streak} giorni" if streak > 0 else "Inizia oggi!"
        mult = profile['streak_multiplier']
        lines.append(f"║  Streak: {streak_display:>20} (x{mult:.1f})  ║")

        # Stats
        lines.append("╠═══════════════════════════════════════════╣")
        lines.append(f"║  Task completati: {profile.get('total_tasks_completed', 0):>22}  ║")
        lines.append(f"║  Minuti di focus: {profile.get('total_focus_minutes', 0):>22}  ║")
        lines.append(f"║  Progetti completati: {profile.get('total_projects_completed', 0):>18}  ║")

        # Achievements
        achievements = self.get_unlocked_achievements()
        lines.append("╠═══════════════════════════════════════════╣")
        lines.append(f"║  🏆 Achievements: {len(achievements):>23}  ║")

        lines.append("╚═══════════════════════════════════════════╝")

        return "\n".join(lines)

    def generate_achievements_display(self) -> str:
        """Genera display ASCII degli achievements."""
        all_achievements = self.get_all_achievements()

        lines = ["╔═══════════════════════════════════════════╗",
                "║            🏆 ACHIEVEMENTS                 ║",
                "╠═══════════════════════════════════════════╣"]

        unlocked = [a for a in all_achievements if a.unlocked]
        locked = [a for a in all_achievements if not a.unlocked]

        # Mostra sbloccati prima
        if unlocked:
            for ach in unlocked:
                name = f"{ach.icon} {ach.name}"[:35]
                lines.append(f"║  ✅ {name:<36}  ║")

        if locked:
            lines.append("╠───────────────────────────────────────────╣")
            for ach in locked[:5]:  # Mostra solo primi 5 locked
                name = f"🔒 {ach.name}"[:35]
                lines.append(f"║  {name:<38}  ║")
            if len(locked) > 5:
                lines.append(f"║     ... e altri {len(locked)-5} da sbloccare          ║")

        lines.append("╚═══════════════════════════════════════════╝")
        return "\n".join(lines)
