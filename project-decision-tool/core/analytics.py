"""
Analytics - Statistiche e insights sulla produttività.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from .database import Database


class Analytics:
    """
    Sistema di analytics per tracciare e visualizzare
    la produttività nel tempo.
    """

    def __init__(self, db: Database):
        self.db = db

    def get_daily_summary(self, date: str = None) -> Dict:
        """Ritorna il sommario di un giorno specifico."""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        stats = self.db.get_or_create_daily_stats(date)
        sessions = self.db.get_focus_sessions(date=date)

        # Calcola media interruzioni
        if sessions:
            avg_interruptions = sum(s['interruptions'] for s in sessions) / len(sessions)
            completed_sessions = sum(1 for s in sessions if s['completed'])
        else:
            avg_interruptions = 0
            completed_sessions = 0

        return {
            'date': date,
            'focus_minutes': stats.get('focus_minutes', 0),
            'focus_hours': round(stats.get('focus_minutes', 0) / 60, 1),
            'tasks_completed': stats.get('tasks_completed', 0),
            'points_earned': stats.get('points_earned', 0),
            'decisions_made': stats.get('decisions_made', 0),
            'total_sessions': len(sessions),
            'completed_sessions': completed_sessions,
            'avg_interruptions': round(avg_interruptions, 1),
            'mood_avg': stats.get('mood_avg'),
        }

    def get_weekly_summary(self) -> Dict:
        """Ritorna il sommario dell'ultima settimana."""
        stats = self.db.get_stats_range(days=7)

        if not stats:
            return self._empty_summary()

        total_focus = sum(s.get('focus_minutes', 0) for s in stats)
        total_tasks = sum(s.get('tasks_completed', 0) for s in stats)
        total_points = sum(s.get('points_earned', 0) for s in stats)
        active_days = sum(1 for s in stats if s.get('focus_minutes', 0) > 0)

        # Trova giorno migliore
        best_day = max(stats, key=lambda s: s.get('focus_minutes', 0))

        return {
            'period': 'Ultimi 7 giorni',
            'total_focus_minutes': total_focus,
            'total_focus_hours': round(total_focus / 60, 1),
            'total_tasks_completed': total_tasks,
            'total_points_earned': total_points,
            'active_days': active_days,
            'avg_focus_per_day': round(total_focus / 7, 0),
            'avg_tasks_per_day': round(total_tasks / 7, 1),
            'best_day': best_day.get('date'),
            'best_day_focus': best_day.get('focus_minutes', 0),
            'daily_breakdown': stats
        }

    def get_monthly_summary(self) -> Dict:
        """Ritorna il sommario dell'ultimo mese."""
        stats = self.db.get_stats_range(days=30)

        if not stats:
            return self._empty_summary()

        total_focus = sum(s.get('focus_minutes', 0) for s in stats)
        total_tasks = sum(s.get('tasks_completed', 0) for s in stats)
        total_points = sum(s.get('points_earned', 0) for s in stats)
        active_days = sum(1 for s in stats if s.get('focus_minutes', 0) > 0)

        return {
            'period': 'Ultimi 30 giorni',
            'total_focus_minutes': total_focus,
            'total_focus_hours': round(total_focus / 60, 1),
            'total_tasks_completed': total_tasks,
            'total_points_earned': total_points,
            'active_days': active_days,
            'consistency_rate': round(active_days / 30 * 100, 0),
            'avg_focus_per_active_day': round(total_focus / max(1, active_days), 0),
        }

    def _empty_summary(self) -> Dict:
        """Ritorna un sommario vuoto."""
        return {
            'total_focus_minutes': 0,
            'total_tasks_completed': 0,
            'message': 'Nessun dato disponibile. Inizia a lavorare!'
        }

    def get_productivity_score(self) -> Tuple[int, str]:
        """
        Calcola un punteggio di produttività 0-100.
        Ritorna (score, descrizione).
        """
        weekly = self.get_weekly_summary()
        profile = self.db.get_user_profile()

        score = 0
        factors = []

        # Focus time (max 35 punti)
        # Target: 4 ore al giorno = 28 ore settimana
        target_weekly_focus = 28 * 60  # minuti
        focus_score = min(35, int(weekly['total_focus_minutes'] / target_weekly_focus * 35))
        score += focus_score
        if focus_score >= 30:
            factors.append("Eccellente tempo di focus 🧘")
        elif focus_score >= 20:
            factors.append("Buon tempo di focus")

        # Consistency (max 25 punti)
        consistency_score = int(weekly['active_days'] / 7 * 25)
        score += consistency_score
        if consistency_score >= 20:
            factors.append("Molto costante 📅")

        # Streak (max 20 punti)
        streak = profile.get('current_streak', 0)
        streak_score = min(20, streak * 3)
        score += streak_score
        if streak >= 7:
            factors.append(f"Streak impressionante: {streak} giorni 🔥")

        # Tasks completati (max 20 punti)
        # Target: 3 task al giorno = 21/settimana
        target_tasks = 21
        tasks_score = min(20, int(weekly['total_tasks_completed'] / target_tasks * 20))
        score += tasks_score
        if tasks_score >= 15:
            factors.append("Tanti task completati ✅")

        # Descrizione basata sullo score
        if score >= 90:
            description = "🌟 FENOMENALE! Sei un mostro di produttività!"
        elif score >= 75:
            description = "🚀 ECCELLENTE! Stai andando alla grande!"
        elif score >= 60:
            description = "💪 BUONO! Continua così!"
        elif score >= 40:
            description = "📈 DISCRETO. Puoi migliorare!"
        elif score >= 20:
            description = "🌱 IN CRESCITA. Ogni giorno un passo avanti."
        else:
            description = "🎯 INIZIA ORA! Il primo passo è il più importante."

        return score, description

    def get_insights(self) -> List[Dict]:
        """
        Genera insights basati sui dati.
        """
        insights = []
        weekly = self.get_weekly_summary()
        daily = self.get_daily_summary()
        profile = self.db.get_user_profile()

        # Insight focus
        if weekly['total_focus_hours'] < 10:
            insights.append({
                'type': 'warning',
                'icon': '⚠️',
                'title': 'Focus basso questa settimana',
                'message': f"Solo {weekly['total_focus_hours']}h di focus. Prova ad aggiungere 1 pomodoro in più al giorno.",
                'action': 'Inizia un pomodoro ora!'
            })
        elif weekly['total_focus_hours'] >= 25:
            insights.append({
                'type': 'success',
                'icon': '🏆',
                'title': 'Settimana super produttiva!',
                'message': f"{weekly['total_focus_hours']}h di focus! Sei nel top!",
                'action': None
            })

        # Insight consistency
        if weekly['active_days'] < 4:
            insights.append({
                'type': 'tip',
                'icon': '💡',
                'title': 'Migliora la costanza',
                'message': f"Solo {weekly['active_days']}/7 giorni attivi. Anche 15 minuti contano!",
                'action': 'Imposta un promemoria giornaliero'
            })

        # Insight streak
        streak = profile.get('current_streak', 0)
        if streak == 0:
            insights.append({
                'type': 'urgent',
                'icon': '🔥',
                'title': 'Inizia la tua streak!',
                'message': "Non hai una streak attiva. Fai qualcosa oggi per iniziarne una!",
                'action': 'Completa un task veloce'
            })
        elif streak >= 7:
            next_milestone = 14 if streak < 14 else (30 if streak < 30 else streak + 1)
            insights.append({
                'type': 'motivation',
                'icon': '🔥',
                'title': f'Streak di {streak} giorni!',
                'message': f"Prossimo traguardo: {next_milestone} giorni. Non mollare!",
                'action': None
            })

        # Insight orario migliore
        sessions = self.db.get_focus_sessions(limit=50)
        if sessions:
            morning_sessions = sum(1 for s in sessions
                                   if s.get('started_at') and
                                   '0' <= s['started_at'][11:13] < '12')
            if morning_sessions > len(sessions) * 0.6:
                insights.append({
                    'type': 'info',
                    'icon': '🌅',
                    'title': 'Sei un mattiniero!',
                    'message': 'La maggior parte del tuo focus avviene di mattina. Sfruttalo!',
                    'action': None
                })

        # Insight task overdue
        tasks = self.db.get_pending_tasks()
        overdue_tasks = [t for t in tasks if t.get('due_date') and t['due_date'] < datetime.now().isoformat()]
        if len(overdue_tasks) > 2:
            insights.append({
                'type': 'warning',
                'icon': '⏰',
                'title': f'{len(overdue_tasks)} task in ritardo!',
                'message': 'Hai task scaduti. Occupatene o rimuovili dalla lista.',
                'action': 'Rivedi i task in ritardo'
            })

        return insights

    def get_best_time_to_work(self) -> Dict:
        """Analizza quando l'utente è più produttivo."""
        sessions = self.db.get_focus_sessions(limit=100)

        if not sessions:
            return {'message': 'Non abbastanza dati'}

        # Raggruppa per fascia oraria
        time_slots = defaultdict(lambda: {'count': 0, 'completed': 0, 'interruptions': 0})

        for session in sessions:
            started = session.get('started_at')
            if not started:
                continue

            hour = int(started[11:13])

            if 5 <= hour < 9:
                slot = 'early_morning'
            elif 9 <= hour < 12:
                slot = 'morning'
            elif 12 <= hour < 14:
                slot = 'lunch'
            elif 14 <= hour < 17:
                slot = 'afternoon'
            elif 17 <= hour < 20:
                slot = 'evening'
            else:
                slot = 'night'

            time_slots[slot]['count'] += 1
            if session.get('completed'):
                time_slots[slot]['completed'] += 1
            time_slots[slot]['interruptions'] += session.get('interruptions', 0)

        # Trova il momento migliore (più sessioni completate, meno interruzioni)
        best_slot = None
        best_score = -1

        slot_names = {
            'early_morning': '🌅 Prima mattina (5-9)',
            'morning': '☀️ Mattina (9-12)',
            'lunch': '🍽️ Pranzo (12-14)',
            'afternoon': '🌤️ Pomeriggio (14-17)',
            'evening': '🌆 Sera (17-20)',
            'night': '🌙 Notte (20+)'
        }

        for slot, data in time_slots.items():
            if data['count'] == 0:
                continue
            completion_rate = data['completed'] / data['count']
            avg_interruptions = data['interruptions'] / data['count']
            score = completion_rate * 100 - avg_interruptions * 10

            if score > best_score:
                best_score = score
                best_slot = slot

        return {
            'best_time': slot_names.get(best_slot, 'Mattina'),
            'time_breakdown': {
                slot_names.get(k, k): {
                    'sessions': v['count'],
                    'completion_rate': round(v['completed'] / max(1, v['count']) * 100, 0),
                    'avg_interruptions': round(v['interruptions'] / max(1, v['count']), 1)
                }
                for k, v in time_slots.items()
            },
            'recommendation': f"Il tuo momento migliore per lavorare è {slot_names.get(best_slot, 'la mattina')}"
        }

    def generate_weekly_report(self) -> str:
        """Genera un report settimanale testuale."""
        weekly = self.get_weekly_summary()
        score, score_desc = self.get_productivity_score()
        insights = self.get_insights()
        profile = self.db.get_user_profile()

        lines = [
            "╔═══════════════════════════════════════════════════╗",
            "║           📊 REPORT SETTIMANALE                    ║",
            "╠═══════════════════════════════════════════════════╣",
            f"║  Periodo: {weekly.get('period', 'Ultimi 7 giorni'):>38}  ║",
            "╠═══════════════════════════════════════════════════╣",
            "",
            f"  🧘 Focus totale:     {weekly['total_focus_hours']:.1f} ore",
            f"  ✅ Task completati:  {weekly['total_tasks_completed']}",
            f"  📅 Giorni attivi:    {weekly['active_days']}/7",
            f"  ⭐ Punti guadagnati: {weekly['total_points_earned']}",
            f"  🔥 Streak attuale:   {profile.get('current_streak', 0)} giorni",
            "",
            "╠═══════════════════════════════════════════════════╣",
            f"  PUNTEGGIO PRODUTTIVITÀ: {score}/100",
            f"  {score_desc}",
            "╠═══════════════════════════════════════════════════╣",
            "  📈 INSIGHTS:",
        ]

        for insight in insights[:3]:
            lines.append(f"  {insight['icon']} {insight['title']}")

        if weekly.get('best_day'):
            lines.append("")
            lines.append(f"  🏆 Giorno migliore: {weekly['best_day']} ({weekly['best_day_focus']} min)")

        lines.extend([
            "",
            "╚═══════════════════════════════════════════════════╝"
        ])

        return "\n".join(lines)

    def generate_mini_chart(self, data: List[int], width: int = 20) -> str:
        """Genera un mini grafico ASCII."""
        if not data:
            return "▁" * width

        max_val = max(data) if max(data) > 0 else 1
        chars = " ▁▂▃▄▅▆▇█"

        result = ""
        for val in data[-width:]:
            idx = int(val / max_val * (len(chars) - 1))
            result += chars[idx]

        return result

    def get_focus_trend(self, days: int = 7) -> str:
        """Ritorna il trend del focus come mini grafico."""
        stats = self.db.get_stats_range(days=days)
        values = [s.get('focus_minutes', 0) for s in reversed(stats)]
        return self.generate_mini_chart(values, days)
