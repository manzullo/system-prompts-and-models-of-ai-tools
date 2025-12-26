"""
Focus Mode - Sistema Pomodoro avanzato con tracking e anti-distrazione.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field
from enum import Enum

from .database import Database


class SessionType(Enum):
    """Tipi di sessione focus."""
    POMODORO = "pomodoro"      # 25 min standard
    SHORT = "short"            # 15 min
    LONG = "long"              # 50 min
    CUSTOM = "custom"          # Personalizzato
    BREAK_SHORT = "break_short"  # Pausa breve 5 min
    BREAK_LONG = "break_long"    # Pausa lunga 15 min


@dataclass
class FocusSession:
    """Rappresenta una sessione di focus attiva."""
    id: Optional[int] = None
    task_id: Optional[int] = None
    project_id: Optional[int] = None
    task_name: str = ""
    project_name: str = ""

    session_type: SessionType = SessionType.POMODORO
    duration_minutes: int = 25
    elapsed_seconds: int = 0

    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    is_running: bool = False
    is_completed: bool = False

    interruptions: int = 0
    mood_before: Optional[int] = None
    mood_after: Optional[int] = None
    notes: str = ""

    # Callbacks
    on_tick: Optional[Callable] = None
    on_complete: Optional[Callable] = None
    on_interrupt: Optional[Callable] = None

    @property
    def remaining_seconds(self) -> int:
        """Secondi rimanenti."""
        total = self.duration_minutes * 60
        return max(0, total - self.elapsed_seconds)

    @property
    def progress(self) -> float:
        """Percentuale di completamento."""
        total = self.duration_minutes * 60
        if total <= 0:
            return 0.0
        return min(100.0, (self.elapsed_seconds / total) * 100)

    @property
    def time_display(self) -> str:
        """Tempo rimanente formattato MM:SS."""
        remaining = self.remaining_seconds
        minutes = remaining // 60
        seconds = remaining % 60
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def elapsed_display(self) -> str:
        """Tempo trascorso formattato MM:SS."""
        minutes = self.elapsed_seconds // 60
        seconds = self.elapsed_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


class FocusMode:
    """
    Gestore delle sessioni di focus.
    Include timer, tracking interruzioni, e statistiche.
    """

    # Presets di durata
    PRESETS = {
        SessionType.POMODORO: 25,
        SessionType.SHORT: 15,
        SessionType.LONG: 50,
        SessionType.BREAK_SHORT: 5,
        SessionType.BREAK_LONG: 15,
    }

    def __init__(self, db: Database):
        self.db = db
        self.current_session: Optional[FocusSession] = None
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._pause_flag = threading.Event()

        # Contatori per la sessione corrente
        self.pomodoros_today = 0
        self.focus_minutes_today = 0
        self._load_today_stats()

    def _load_today_stats(self):
        """Carica le statistiche di oggi."""
        today = datetime.now().strftime('%Y-%m-%d')
        sessions = self.db.get_focus_sessions(date=today)

        self.pomodoros_today = sum(1 for s in sessions
                                   if s['completed'] and s['duration_minutes'] >= 25)
        self.focus_minutes_today = sum(s['duration_minutes'] for s in sessions
                                       if s['completed'])

    def start_session(self,
                     session_type: SessionType = SessionType.POMODORO,
                     duration_minutes: int = None,
                     task_id: int = None,
                     project_id: int = None,
                     task_name: str = "",
                     project_name: str = "",
                     mood_before: int = None,
                     on_tick: Callable = None,
                     on_complete: Callable = None) -> FocusSession:
        """
        Inizia una nuova sessione di focus.
        """
        # Ferma eventuale sessione precedente
        if self.current_session and self.current_session.is_running:
            self.stop_session(completed=False)

        # Determina durata
        if duration_minutes is None:
            duration_minutes = self.PRESETS.get(session_type, 25)

        # Crea sessione nel database
        db_session_id = self.db.create_focus_session(
            duration_minutes=duration_minutes,
            task_id=task_id,
            project_id=project_id,
            mood_before=mood_before
        )

        # Crea oggetto sessione
        self.current_session = FocusSession(
            id=db_session_id,
            task_id=task_id,
            project_id=project_id,
            task_name=task_name,
            project_name=project_name,
            session_type=session_type,
            duration_minutes=duration_minutes,
            started_at=datetime.now(),
            is_running=True,
            mood_before=mood_before,
            on_tick=on_tick,
            on_complete=on_complete
        )

        # Avvia timer thread
        self._stop_flag.clear()
        self._pause_flag.clear()
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()

        return self.current_session

    def _timer_loop(self):
        """Loop del timer che gira in background."""
        while not self._stop_flag.is_set():
            if not self._pause_flag.is_set():
                if self.current_session:
                    self.current_session.elapsed_seconds += 1

                    # Callback tick
                    if self.current_session.on_tick:
                        try:
                            self.current_session.on_tick(self.current_session)
                        except:
                            pass

                    # Check completamento
                    if self.current_session.remaining_seconds <= 0:
                        self._complete_session()
                        break

            time.sleep(1)

    def _complete_session(self):
        """Gestisce il completamento della sessione."""
        if not self.current_session:
            return

        self.current_session.is_completed = True
        self.current_session.is_running = False

        # Aggiorna database
        self.db.end_focus_session(
            session_id=self.current_session.id,
            completed=True,
            interruptions=self.current_session.interruptions,
            mood_after=self.current_session.mood_after,
            notes=self.current_session.notes
        )

        # Aggiorna task se presente
        if self.current_session.task_id:
            task = self.db.get_task(self.current_session.task_id)
            if task:
                new_logged = task['logged_minutes'] + self.current_session.duration_minutes
                self.db.update_task(
                    self.current_session.task_id,
                    logged_minutes=new_logged
                )

        # Aggiorna progetto se presente
        if self.current_session.project_id:
            project = self.db.get_project(self.current_session.project_id)
            if project:
                hours_added = self.current_session.duration_minutes / 60
                new_logged = project['logged_hours'] + hours_added
                self.db.update_project(
                    self.current_session.project_id,
                    logged_hours=new_logged
                )

        # Aggiorna stats giornaliere
        self.db.update_daily_stats(
            focus_minutes=self.current_session.duration_minutes
        )

        # Aggiorna contatori locali
        self.focus_minutes_today += self.current_session.duration_minutes
        if self.current_session.duration_minutes >= 25:
            self.pomodoros_today += 1

        # Callback completamento
        if self.current_session.on_complete:
            try:
                self.current_session.on_complete(self.current_session)
            except:
                pass

    def pause_session(self) -> bool:
        """Mette in pausa la sessione corrente."""
        if not self.current_session or not self.current_session.is_running:
            return False

        self._pause_flag.set()
        self.current_session.paused_at = datetime.now()
        return True

    def resume_session(self) -> bool:
        """Riprende la sessione in pausa."""
        if not self.current_session or self._stop_flag.is_set():
            return False

        self._pause_flag.clear()
        self.current_session.paused_at = None
        return True

    def stop_session(self, completed: bool = False,
                    mood_after: int = None,
                    notes: str = None) -> Optional[FocusSession]:
        """
        Ferma la sessione corrente.
        completed=False se interrotta, True se finita volontariamente.
        """
        if not self.current_session:
            return None

        self._stop_flag.set()

        if self._timer_thread and self._timer_thread.is_alive():
            self._timer_thread.join(timeout=2)

        self.current_session.is_running = False
        self.current_session.is_completed = completed
        if mood_after:
            self.current_session.mood_after = mood_after
        if notes:
            self.current_session.notes = notes

        # Salva nel database
        actual_minutes = self.current_session.elapsed_seconds // 60

        self.db.end_focus_session(
            session_id=self.current_session.id,
            completed=completed,
            interruptions=self.current_session.interruptions,
            mood_after=mood_after,
            notes=notes
        )

        # Se completata, aggiorna stats
        if completed and actual_minutes > 0:
            self.db.update_daily_stats(focus_minutes=actual_minutes)
            self.focus_minutes_today += actual_minutes

        session = self.current_session
        self.current_session = None
        return session

    def log_interruption(self, description: str = "") -> bool:
        """Registra un'interruzione durante la sessione."""
        if not self.current_session:
            return False

        self.current_session.interruptions += 1

        if self.current_session.id:
            self.db.log_distraction(
                session_id=self.current_session.id,
                description=description
            )

        if self.current_session.on_interrupt:
            try:
                self.current_session.on_interrupt(self.current_session, description)
            except:
                pass

        return True

    def add_time(self, minutes: int = 5) -> bool:
        """Aggiunge tempo alla sessione corrente."""
        if not self.current_session:
            return False

        self.current_session.duration_minutes += minutes
        return True

    def get_session_status(self) -> Dict:
        """Ritorna lo stato della sessione corrente."""
        if not self.current_session:
            return {
                "active": False,
                "message": "Nessuna sessione attiva"
            }

        session = self.current_session
        return {
            "active": True,
            "running": session.is_running,
            "paused": self._pause_flag.is_set(),
            "type": session.session_type.value,
            "task_name": session.task_name,
            "project_name": session.project_name,
            "time_remaining": session.time_display,
            "time_elapsed": session.elapsed_display,
            "progress": session.progress,
            "interruptions": session.interruptions,
            "duration_minutes": session.duration_minutes
        }

    def get_today_summary(self) -> Dict:
        """Ritorna il sommario di oggi."""
        return {
            "pomodoros_completed": self.pomodoros_today,
            "focus_minutes": self.focus_minutes_today,
            "focus_hours": round(self.focus_minutes_today / 60, 1),
            "suggested_break": self._suggest_break()
        }

    def _suggest_break(self) -> Optional[str]:
        """Suggerisce tipo di pausa basato sul lavoro fatto."""
        if self.pomodoros_today >= 4:
            return "Hai fatto 4+ pomodori! Prendi una pausa lunga (15-30 min) 🧘"
        elif self.focus_minutes_today >= 50:
            return "Buon lavoro! Una pausa breve (5-10 min) ti farebbe bene ☕"
        return None

    def suggest_next_session_type(self) -> SessionType:
        """Suggerisce il tipo di prossima sessione."""
        if self.current_session and self.current_session.is_completed:
            # Dopo un pomodoro, suggerisci pausa
            if self.pomodoros_today % 4 == 0 and self.pomodoros_today > 0:
                return SessionType.BREAK_LONG
            return SessionType.BREAK_SHORT

        # Default: pomodoro standard
        return SessionType.POMODORO

    def get_focus_tips(self) -> List[str]:
        """Ritorna consigli per mantenere il focus."""
        tips = [
            "🔇 Metti il telefono in modalità aereo",
            "🎧 Usa musica ambient o rumore bianco",
            "💧 Tieni una bottiglia d'acqua vicina",
            "🚪 Chiudi tutte le tab non necessarie",
            "📝 Scrivi le distrazioni invece di seguirle",
            "⏰ Prometti a te stesso: 'Solo fino alla fine del timer'",
            "🎯 Concentrati su UNA cosa alla volta",
            "🪑 Assumi una postura corretta",
            "💡 Assicurati che la luce sia adeguata",
            "🌡️ Controlla che la temperatura sia confortevole"
        ]

        # Consigli basati sul contesto
        if self.pomodoros_today == 0:
            tips.insert(0, "💪 Primo pomodoro della giornata! Inizia forte!")
        elif self.pomodoros_today >= 6:
            tips.insert(0, "🌟 Wow, 6+ pomodori! Sei una macchina!")

        if self.current_session and self.current_session.interruptions > 0:
            tips.insert(0, f"⚠️ {self.current_session.interruptions} interruzioni - identifica la causa!")

        return tips[:5]  # Ritorna solo i top 5

    def generate_progress_bar(self, width: int = 30) -> str:
        """Genera una progress bar ASCII."""
        if not self.current_session:
            return "[" + "-" * width + "]"

        progress = self.current_session.progress / 100
        filled = int(width * progress)
        empty = width - filled

        bar = "█" * filled + "░" * empty
        return f"[{bar}] {self.current_session.progress:.0f}%"

    def generate_timer_display(self) -> str:
        """Genera display ASCII del timer."""
        if not self.current_session:
            return "⏱️ --:--"

        session = self.current_session
        status = "▶️" if session.is_running and not self._pause_flag.is_set() else "⏸️"

        lines = [
            f"╔══════════════════════════════════╗",
            f"║  {status} {session.time_display}                       ║",
            f"║  {self.generate_progress_bar(28)}  ║",
            f"╚══════════════════════════════════╝"
        ]

        if session.task_name:
            task_line = session.task_name[:30].center(32)
            lines.insert(1, f"║ {task_line} ║")

        return "\n".join(lines)
