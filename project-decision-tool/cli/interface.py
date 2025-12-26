"""
CLI Interface - Interfaccia a linea di comando interattiva.
"""

import os
import sys
import time
import threading
from datetime import datetime
from typing import Optional, List, Callable

from core.database import Database
from core.project import Project, ProjectStatus, EnergyLevel
from core.task import Task, TaskStatus
from core.decision_engine import DecisionEngine, DecisionMode, DecisionContext
from core.focus_mode import FocusMode, SessionType
from core.gamification import GamificationSystem
from core.anti_procrastination import AntiProcrastination, ProcrastinationReason
from core.analytics import Analytics


class Colors:
    """Codici colore ANSI."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_BLUE = '\033[44m'


class CLI:
    """Interfaccia CLI principale."""

    def __init__(self, db_path: str = None):
        self.db = Database(db_path)
        self.decision_engine = DecisionEngine(self.db)
        self.focus_mode = FocusMode(self.db)
        self.gamification = GamificationSystem(self.db)
        self.anti_proc = AntiProcrastination(self.db)
        self.analytics = Analytics(self.db)

        self.running = True
        self._focus_display_thread = None

    def clear_screen(self):
        """Pulisce lo schermo."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, title: str):
        """Stampa un header."""
        width = 50
        print(f"\n{Colors.CYAN}{'═' * width}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}  {title.center(width - 4)}{Colors.RESET}")
        print(f"{Colors.CYAN}{'═' * width}{Colors.RESET}\n")

    def print_success(self, message: str):
        print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

    def print_error(self, message: str):
        print(f"{Colors.RED}✗ {message}{Colors.RESET}")

    def print_warning(self, message: str):
        print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

    def print_info(self, message: str):
        print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")

    def input_prompt(self, prompt: str, default: str = None) -> str:
        """Input con prompt colorato."""
        if default:
            prompt = f"{prompt} [{default}]"
        result = input(f"{Colors.CYAN}→ {prompt}: {Colors.RESET}").strip()
        return result if result else default

    def input_number(self, prompt: str, min_val: int = 1, max_val: int = 10,
                    default: int = 5) -> int:
        """Input numerico con validazione."""
        while True:
            result = self.input_prompt(f"{prompt} ({min_val}-{max_val})", str(default))
            try:
                num = int(result)
                if min_val <= num <= max_val:
                    return num
                self.print_error(f"Inserisci un numero tra {min_val} e {max_val}")
            except ValueError:
                self.print_error("Inserisci un numero valido")

    def input_choice(self, prompt: str, options: List[str]) -> int:
        """Input scelta da opzioni."""
        print(f"\n{prompt}")
        for i, option in enumerate(options, 1):
            print(f"  {Colors.CYAN}{i}.{Colors.RESET} {option}")

        while True:
            choice = self.input_prompt("Scelta")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    return idx
                self.print_error(f"Scegli tra 1 e {len(options)}")
            except ValueError:
                self.print_error("Inserisci un numero")

    def run(self):
        """Loop principale dell'applicazione."""
        self.clear_screen()
        self._show_welcome()

        # Aggiorna streak
        streak, increased, achievements = self.gamification.update_streak()
        if increased and streak > 1:
            self.print_success(f"🔥 Streak: {streak} giorni!")
        for ach in achievements:
            self._show_achievement_unlocked(ach)

        while self.running:
            try:
                self._show_main_menu()
            except KeyboardInterrupt:
                print("\n")
                self._confirm_exit()
            except Exception as e:
                self.print_error(f"Errore: {e}")
                input("Premi Invio per continuare...")

    def _show_welcome(self):
        """Mostra schermata di benvenuto."""
        profile = self.gamification.get_profile()
        level = profile['level_info']

        print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════╗
║                                                             ║
║   {Colors.BOLD}🎯 PROJECT DECISION TOOL{Colors.RESET}{Colors.CYAN}                               ║
║                                                             ║
║   Il tuo assistente per:                                    ║
║   • Decidere su cosa lavorare                               ║
║   • Mantenere il focus                                      ║
║   • Battere la procrastinazione                             ║
║                                                             ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
""")

        print(f"  Bentornato, {Colors.BOLD}{profile.get('username', 'User')}{Colors.RESET}!")
        print(f"  {level.icon} Livello {level.level}: {level.name}")
        print(f"  🔥 Streak: {profile['current_streak']} giorni | ⭐ {profile['total_points']} punti")
        print()

        # Daily insight
        insights = self.analytics.get_insights()
        if insights:
            insight = insights[0]
            print(f"  {insight['icon']} {Colors.DIM}{insight['title']}{Colors.RESET}")

        input(f"\n  {Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _show_main_menu(self):
        """Mostra il menu principale."""
        self.clear_screen()

        # Mini status bar
        profile = self.gamification.get_profile()
        today = self.analytics.get_daily_summary()
        print(f"{Colors.DIM}─── Lv.{profile['level_info'].level} {profile['level_info'].icon} │ "
              f"🔥 {profile['current_streak']} │ "
              f"⭐ {profile['total_points']} │ "
              f"Oggi: {today['focus_minutes']}min ───{Colors.RESET}")

        self.print_header("MENU PRINCIPALE")

        menu_options = [
            ("🎯", "Cosa dovrei fare adesso?", "decision"),
            ("⏱️", "Inizia sessione Focus", "focus"),
            ("📋", "Gestisci Progetti", "projects"),
            ("✅", "Gestisci Task", "tasks"),
            ("📊", "Statistiche & Analytics", "stats"),
            ("🏆", "Profilo & Achievements", "profile"),
            ("💡", "Aiuto Anti-Procrastinazione", "anti_proc"),
            ("⚙️", "Impostazioni", "settings"),
            ("🚪", "Esci", "exit"),
        ]

        for i, (icon, label, _) in enumerate(menu_options, 1):
            print(f"  {Colors.CYAN}{i}.{Colors.RESET} {icon} {label}")

        print()
        choice = self.input_prompt("Scelta")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(menu_options):
                action = menu_options[idx][2]
                self._execute_menu_action(action)
        except ValueError:
            # Comandi rapidi
            if choice.lower() in ['q', 'exit', 'quit']:
                self._confirm_exit()
            elif choice.lower() in ['f', 'focus']:
                self._start_focus_menu()
            elif choice.lower() in ['d', '?']:
                self._get_recommendation()

    def _execute_menu_action(self, action: str):
        """Esegue l'azione del menu."""
        actions = {
            'decision': self._get_recommendation,
            'focus': self._start_focus_menu,
            'projects': self._manage_projects_menu,
            'tasks': self._manage_tasks_menu,
            'stats': self._show_stats_menu,
            'profile': self._show_profile,
            'anti_proc': self._anti_procrastination_menu,
            'settings': self._settings_menu,
            'exit': self._confirm_exit,
        }

        handler = actions.get(action)
        if handler:
            handler()

    # === DECISION ENGINE ===

    def _get_recommendation(self):
        """Ottiene e mostra una raccomandazione."""
        self.clear_screen()
        self.print_header("🎯 COSA FARE ADESSO?")

        # Chiedi contesto
        print("Prima, alcune domande veloci...\n")

        energy_options = ["🔋 Bassa", "🔋🔋 Media", "🔋🔋🔋 Alta", "⚡ Al massimo!"]
        energy_idx = self.input_choice("Come ti senti in termini di energia?", energy_options)
        energy_map = [EnergyLevel.LOW, EnergyLevel.MEDIUM, EnergyLevel.HIGH, EnergyLevel.EXTREME]
        energy = energy_map[energy_idx]

        time_options = ["15 minuti", "30 minuti", "1 ora", "2+ ore"]
        time_idx = self.input_choice("Quanto tempo hai?", time_options)
        time_map = [15, 30, 60, 120]
        available_time = time_map[time_idx]

        mood = self.input_number("Mood attuale", 1, 10, 5)

        context = DecisionContext(
            current_energy=energy,
            available_minutes=available_time,
            mood=mood
        )

        # Modalità decisione
        mode_options = [
            "🧠 Intelligente (considera tutto)",
            "⏰ Urgente (deadline e urgenza)",
            "🔋 Match Energia (adatto alla tua energia)",
            "⚡ Quick Wins (task veloci)",
            "🎲 Casuale tra i top 3",
        ]
        mode_idx = self.input_choice("Modalità decisione:", mode_options)
        modes = [DecisionMode.SMART, DecisionMode.URGENT, DecisionMode.ENERGY_MATCH,
                DecisionMode.QUICK_WINS, DecisionMode.RANDOM_TOP3]
        mode = modes[mode_idx]

        print(f"\n{Colors.DIM}Analizzando...{Colors.RESET}\n")
        time.sleep(0.5)

        # Ottieni raccomandazione
        rec = self.decision_engine.get_recommendation(context, mode)

        # Mostra risultato
        self._display_recommendation(rec)

        # Opzioni post-raccomandazione
        print("\n" + "─" * 50)
        options = ["▶️ Inizia sessione Focus su questo", "🔄 Altra raccomandazione", "⬅️ Torna al menu"]
        choice = self.input_choice("Cosa vuoi fare?", options)

        if choice == 0:
            self._start_focus_on_recommendation(rec)
        elif choice == 1:
            self._get_recommendation()

    def _display_recommendation(self, rec):
        """Mostra la raccomandazione formattata."""
        if not rec.project and not rec.task:
            self.print_warning("Non ho trovato progetti o task attivi.")
            print("Crea un nuovo progetto per iniziare!")
            return

        print(f"{Colors.GREEN}╔═══════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.GREEN}║  {Colors.BOLD}RACCOMANDAZIONE{Colors.RESET}{Colors.GREEN}                                  ║{Colors.RESET}")
        print(f"{Colors.GREEN}╠═══════════════════════════════════════════════════╣{Colors.RESET}")

        if rec.project:
            print(f"{Colors.GREEN}║{Colors.RESET}  📁 Progetto: {Colors.BOLD}{rec.project.name[:35]:<35}{Colors.RESET} {Colors.GREEN}║{Colors.RESET}")

        if rec.task:
            print(f"{Colors.GREEN}║{Colors.RESET}  ✅ Task: {rec.task.name[:39]:<39} {Colors.GREEN}║{Colors.RESET}")

        print(f"{Colors.GREEN}║{Colors.RESET}  📊 Confidence: {rec.confidence * 100:.0f}%{' ' * 31}{Colors.GREEN}║{Colors.RESET}")
        print(f"{Colors.GREEN}╠═══════════════════════════════════════════════════╣{Colors.RESET}")

        print(f"{Colors.GREEN}║{Colors.RESET}  {Colors.BOLD}Perché:{Colors.RESET}")
        for reason in rec.reasoning[:4]:
            reason_short = reason[:47]
            print(f"{Colors.GREEN}║{Colors.RESET}    • {reason_short}")

        print(f"{Colors.GREEN}╚═══════════════════════════════════════════════════╝{Colors.RESET}")

        # Alternative
        if rec.alternatives:
            print(f"\n{Colors.DIM}Alternative:{Colors.RESET}")
            for i, alt in enumerate(rec.alternatives[:3], 2):
                name = alt.project.name if alt.project else alt.task.name if alt.task else "?"
                print(f"  {i}. {name} (score: {alt.score:.0f})")

    def _start_focus_on_recommendation(self, rec):
        """Inizia focus sulla raccomandazione."""
        task_id = rec.task.id if rec.task else None
        project_id = rec.project.id if rec.project else None
        task_name = rec.task.name if rec.task else ""
        project_name = rec.project.name if rec.project else ""

        self._run_focus_session(
            task_id=task_id,
            project_id=project_id,
            task_name=task_name or project_name,
            project_name=project_name
        )

    # === FOCUS MODE ===

    def _start_focus_menu(self):
        """Menu per iniziare una sessione focus."""
        self.clear_screen()
        self.print_header("⏱️ SESSIONE FOCUS")

        # Mostra sommario oggi
        summary = self.focus_mode.get_today_summary()
        print(f"  Oggi: {summary['pomodoros_completed']} pomodori, {summary['focus_minutes']} min")
        if summary['suggested_break']:
            self.print_warning(summary['suggested_break'])
        print()

        # Tipo sessione
        session_options = [
            "🍅 Pomodoro (25 min)",
            "⚡ Breve (15 min)",
            "🧘 Lunga (50 min)",
            "⏱️ Personalizzata",
            "☕ Pausa breve (5 min)",
            "🌴 Pausa lunga (15 min)",
        ]
        session_idx = self.input_choice("Tipo di sessione:", session_options)

        session_types = [SessionType.POMODORO, SessionType.SHORT, SessionType.LONG,
                        SessionType.CUSTOM, SessionType.BREAK_SHORT, SessionType.BREAK_LONG]
        session_type = session_types[session_idx]

        duration = None
        if session_type == SessionType.CUSTOM:
            duration = self.input_number("Durata in minuti", 5, 120, 25)

        # Seleziona task/progetto (opzionale)
        task_id = None
        project_id = None
        task_name = ""
        project_name = ""

        if session_type not in [SessionType.BREAK_SHORT, SessionType.BREAK_LONG]:
            tasks = self.db.get_pending_tasks(limit=5)
            if tasks:
                print("\n📋 Task recenti:")
                for i, t in enumerate(tasks, 1):
                    pname = f"({t.get('project_name', '')})" if t.get('project_name') else ""
                    print(f"  {i}. {t['name']} {pname}")
                print(f"  0. Nessun task specifico")

                choice = self.input_prompt("Seleziona task", "0")
                if choice and choice != "0":
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(tasks):
                            task_id = tasks[idx]['id']
                            task_name = tasks[idx]['name']
                            project_id = tasks[idx].get('project_id')
                            project_name = tasks[idx].get('project_name', '')
                    except:
                        pass

        # Mood prima
        mood_before = self.input_number("Mood prima di iniziare", 1, 10, 5)

        # Inizia sessione
        self._run_focus_session(
            session_type=session_type,
            duration=duration,
            task_id=task_id,
            project_id=project_id,
            task_name=task_name,
            project_name=project_name,
            mood_before=mood_before
        )

    def _run_focus_session(self, session_type: SessionType = SessionType.POMODORO,
                          duration: int = None, task_id: int = None,
                          project_id: int = None, task_name: str = "",
                          project_name: str = "", mood_before: int = None):
        """Esegue una sessione focus con display live."""
        self.clear_screen()

        # Consigli pre-sessione
        print(f"\n{Colors.YELLOW}💡 Prima di iniziare:{Colors.RESET}")
        tips = self.focus_mode.get_focus_tips()
        for tip in tips[:3]:
            print(f"   {tip}")

        input(f"\n{Colors.DIM}Premi Invio quando sei pronto...{Colors.RESET}")

        # Avvia sessione
        session = self.focus_mode.start_session(
            session_type=session_type,
            duration_minutes=duration,
            task_id=task_id,
            project_id=project_id,
            task_name=task_name,
            project_name=project_name,
            mood_before=mood_before
        )

        # Loop display
        try:
            while session.is_running:
                self.clear_screen()
                self._display_focus_timer(session)

                # Menu rapido
                print(f"\n{Colors.DIM}[p] Pausa  [i] Interruzione  [+] +5min  [s] Stop{Colors.RESET}")

                # Check input non-bloccante (semplificato)
                time.sleep(1)

        except KeyboardInterrupt:
            self._handle_focus_interrupt(session)

        # Fine sessione
        if session.is_completed:
            self._handle_focus_complete(session)
        else:
            self._handle_focus_stop(session)

    def _display_focus_timer(self, session):
        """Mostra il timer della sessione."""
        status = "▶️ FOCUS" if not self.focus_mode._pause_flag.is_set() else "⏸️ PAUSA"

        print(f"""
{Colors.CYAN}╔═════════════════════════════════════════════════════╗
║                                                       ║
║               {status}                              ║
║                                                       ║
║                 {Colors.BOLD}{session.time_display:^10}{Colors.RESET}{Colors.CYAN}                        ║
║                                                       ║
║    {self.focus_mode.generate_progress_bar(40)}    ║
║                                                       ║
╚═════════════════════════════════════════════════════╝{Colors.RESET}
""")

        if session.task_name:
            print(f"  📋 {session.task_name}")
        if session.project_name:
            print(f"  📁 {session.project_name}")

        print(f"\n  ⚡ Interruzioni: {session.interruptions}")

        # Messaggio motivazionale a metà
        if 45 <= session.progress <= 55:
            print(f"\n  {Colors.GREEN}💪 Metà strada! Continua così!{Colors.RESET}")
        elif session.progress >= 90:
            print(f"\n  {Colors.GREEN}🏁 Quasi finito! Non mollare!{Colors.RESET}")

    def _handle_focus_interrupt(self, session):
        """Gestisce interruzione della sessione."""
        self.focus_mode.pause_session()
        print(f"\n{Colors.YELLOW}Sessione in pausa.{Colors.RESET}")

        options = ["▶️ Riprendi", "📝 Registra distrazione e riprendi", "🛑 Termina sessione"]
        choice = self.input_choice("Cosa vuoi fare?", options)

        if choice == 0:
            self.focus_mode.resume_session()
        elif choice == 1:
            desc = self.input_prompt("Cosa ti ha distratto?", "")
            self.focus_mode.log_interruption(desc)
            self.focus_mode.resume_session()
        else:
            mood = self.input_number("Mood dopo la sessione", 1, 10, 5)
            self.focus_mode.stop_session(completed=False, mood_after=mood)

    def _handle_focus_complete(self, session):
        """Gestisce completamento sessione."""
        self.clear_screen()

        print(f"""
{Colors.GREEN}
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║            🎉 SESSIONE COMPLETATA! 🎉              ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
{Colors.RESET}""")

        print(f"  ⏱️ Durata: {session.duration_minutes} minuti")
        print(f"  ⚡ Interruzioni: {session.interruptions}")

        # Mood dopo
        mood_after = self.input_number("Mood dopo la sessione", 1, 10, 7)
        session.mood_after = mood_after

        # Punti e achievements
        action = 'pomodoro_no_interruptions' if session.interruptions == 0 else 'pomodoro_completed'
        points, achievements = self.gamification.award_points(action)

        print(f"\n  {Colors.GREEN}+{points} punti!{Colors.RESET}")

        for ach in achievements:
            self._show_achievement_unlocked(ach)

        # Completa task?
        if session.task_id:
            complete = self.input_prompt("Hai completato il task? (s/n)", "n")
            if complete.lower() == 's':
                self.db.complete_task(session.task_id)
                task_points, task_achs = self.gamification.on_task_completed(
                    self.db.get_task(session.task_id)
                )
                print(f"  {Colors.GREEN}+{task_points} punti per task completato!{Colors.RESET}")
                for ach in task_achs:
                    self._show_achievement_unlocked(ach)

        # Suggerimento prossima sessione
        next_type = self.focus_mode.suggest_next_session_type()
        if next_type in [SessionType.BREAK_SHORT, SessionType.BREAK_LONG]:
            print(f"\n  {Colors.YELLOW}☕ Suggerimento: fai una pausa!{Colors.RESET}")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _handle_focus_stop(self, session):
        """Gestisce stop anticipato."""
        print(f"\n{Colors.YELLOW}Sessione terminata anticipatamente.{Colors.RESET}")
        print(f"  Tempo lavorato: {session.elapsed_seconds // 60} minuti")

        # Punti parziali
        if session.elapsed_seconds >= 300:  # Almeno 5 minuti
            points = session.elapsed_seconds // 60
            self.gamification.award_points('focus', base_points=points)
            print(f"  {Colors.GREEN}+{points} punti{Colors.RESET}")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    # === PROJECTS ===

    def _manage_projects_menu(self):
        """Menu gestione progetti."""
        while True:
            self.clear_screen()
            self.print_header("📋 GESTIONE PROGETTI")

            options = [
                "📝 Crea nuovo progetto",
                "📋 Lista progetti attivi",
                "📦 Lista tutti i progetti",
                "✏️ Modifica progetto",
                "✅ Completa progetto",
                "🗑️ Elimina progetto",
                "⬅️ Torna al menu"
            ]

            choice = self.input_choice("Cosa vuoi fare?", options)

            if choice == 0:
                self._create_project()
            elif choice == 1:
                self._list_projects('active')
            elif choice == 2:
                self._list_projects()
            elif choice == 3:
                self._edit_project()
            elif choice == 4:
                self._complete_project()
            elif choice == 5:
                self._delete_project()
            elif choice == 6:
                break

    def _create_project(self):
        """Crea un nuovo progetto."""
        self.print_header("📝 NUOVO PROGETTO")

        name = self.input_prompt("Nome del progetto")
        if not name:
            self.print_error("Il nome è obbligatorio")
            return

        description = self.input_prompt("Descrizione (opzionale)", "")

        print(f"\n{Colors.CYAN}Valutazione progetto (1-10):{Colors.RESET}")
        importance = self.input_number("Importanza (quanto è importante?)", 1, 10, 5)
        urgency = self.input_number("Urgenza (quanto è urgente?)", 1, 10, 5)
        excitement = self.input_number("Entusiasmo (quanto ti entusiasma?)", 1, 10, 5)

        energy_options = ["🔋 Bassa", "🔋🔋 Media", "🔋🔋🔋 Alta", "⚡ Estrema"]
        energy_idx = self.input_choice("Energia richiesta:", energy_options)
        energy_values = ['low', 'medium', 'high', 'extreme']
        energy = energy_values[energy_idx]

        estimated = self.input_number("Ore stimate per completare", 1, 1000, 10)

        deadline = self.input_prompt("Deadline (YYYY-MM-DD, opzionale)", "")

        # Crea progetto
        project_id = self.db.create_project(
            name=name,
            description=description,
            importance=importance,
            urgency=urgency,
            excitement=excitement,
            energy_required=energy,
            estimated_hours=estimated,
            deadline=deadline if deadline else None
        )

        self.print_success(f"Progetto '{name}' creato con ID {project_id}!")

        # Achievement
        points, achievements = self.gamification.award_points('decision_made')
        if achievements:
            for ach in achievements:
                self._show_achievement_unlocked(ach)

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _list_projects(self, status: str = None):
        """Lista progetti."""
        projects = self.db.get_all_projects(status)

        if not projects:
            self.print_warning("Nessun progetto trovato.")
            input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")
            return

        print(f"\n{'─' * 60}")
        for p in projects:
            proj = Project.from_dict(p)
            status_emoji = {
                'active': '🟢',
                'paused': '⏸️',
                'completed': '✅',
                'archived': '📦'
            }
            emoji = status_emoji.get(p['status'], '❓')

            print(f"{emoji} [{p['id']}] {Colors.BOLD}{p['name']}{Colors.RESET}")
            print(f"    I:{p['importance']} U:{p['urgency']} E:{p['excitement']} | "
                  f"{proj.progress:.0f}% | {proj.eisenhower_quadrant}")
            if p.get('deadline'):
                print(f"    📅 Deadline: {p['deadline'][:10]}")
        print(f"{'─' * 60}")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _edit_project(self):
        """Modifica un progetto."""
        project_id = self.input_number("ID del progetto da modificare", 1, 99999, 1)
        project = self.db.get_project(project_id)

        if not project:
            self.print_error("Progetto non trovato")
            return

        print(f"\nModifica: {project['name']}")
        print("(Lascia vuoto per mantenere il valore attuale)\n")

        name = self.input_prompt(f"Nome [{project['name']}]")
        importance = self.input_prompt(f"Importanza [{project['importance']}]")
        urgency = self.input_prompt(f"Urgenza [{project['urgency']}]")
        excitement = self.input_prompt(f"Entusiasmo [{project['excitement']}]")

        updates = {}
        if name:
            updates['name'] = name
        if importance:
            updates['importance'] = int(importance)
        if urgency:
            updates['urgency'] = int(urgency)
        if excitement:
            updates['excitement'] = int(excitement)

        if updates:
            self.db.update_project(project_id, **updates)
            self.print_success("Progetto aggiornato!")
        else:
            self.print_info("Nessuna modifica effettuata")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _complete_project(self):
        """Completa un progetto."""
        project_id = self.input_number("ID del progetto da completare", 1, 99999, 1)
        project = self.db.get_project(project_id)

        if not project:
            self.print_error("Progetto non trovato")
            return

        confirm = self.input_prompt(f"Completare '{project['name']}'? (s/n)", "n")
        if confirm.lower() == 's':
            self.db.update_project(project_id, status='completed',
                                  completed_at=datetime.now().isoformat())
            self.print_success("Progetto completato!")

            points, achievements = self.gamification.on_project_completed(project)
            print(f"  {Colors.GREEN}+{points} punti!{Colors.RESET}")
            for ach in achievements:
                self._show_achievement_unlocked(ach)

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _delete_project(self):
        """Elimina un progetto."""
        project_id = self.input_number("ID del progetto da eliminare", 1, 99999, 1)
        project = self.db.get_project(project_id)

        if not project:
            self.print_error("Progetto non trovato")
            return

        confirm = self.input_prompt(f"ELIMINARE '{project['name']}'? (scrivi 'ELIMINA' per confermare)")
        if confirm == 'ELIMINA':
            self.db.delete_project(project_id)
            self.print_success("Progetto eliminato!")
        else:
            self.print_info("Eliminazione annullata")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    # === TASKS ===

    def _manage_tasks_menu(self):
        """Menu gestione task."""
        while True:
            self.clear_screen()
            self.print_header("✅ GESTIONE TASK")

            options = [
                "📝 Crea nuovo task",
                "📋 Lista task pending",
                "✅ Completa task",
                "🔬 Spacchetta in micro-task",
                "⬅️ Torna al menu"
            ]

            choice = self.input_choice("Cosa vuoi fare?", options)

            if choice == 0:
                self._create_task()
            elif choice == 1:
                self._list_tasks()
            elif choice == 2:
                self._complete_task()
            elif choice == 3:
                self._split_task()
            elif choice == 4:
                break

    def _create_task(self):
        """Crea un nuovo task."""
        self.print_header("📝 NUOVO TASK")

        name = self.input_prompt("Nome del task")
        if not name:
            self.print_error("Il nome è obbligatorio")
            return

        # Seleziona progetto opzionale
        projects = self.db.get_all_projects('active')
        project_id = None

        if projects:
            print("\nProgetti disponibili:")
            for p in projects:
                print(f"  [{p['id']}] {p['name']}")
            print("  [0] Nessun progetto")

            pid = self.input_prompt("Associa a progetto (ID)", "0")
            if pid and pid != "0":
                project_id = int(pid)

        estimated = self.input_number("Minuti stimati", 5, 480, 25)
        priority = self.input_number("Priorità", 1, 10, 5)

        task_id = self.db.create_task(
            name=name,
            project_id=project_id,
            estimated_minutes=estimated,
            priority=priority
        )

        self.print_success(f"Task creato con ID {task_id}!")
        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _list_tasks(self):
        """Lista task pending."""
        tasks = self.db.get_pending_tasks(limit=20)

        if not tasks:
            self.print_warning("Nessun task pending.")
            input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")
            return

        print(f"\n{'─' * 60}")
        for t in tasks:
            task = Task.from_dict(t)
            micro = "  └─" if task.is_micro_task else ""
            emoji = "⬜" if task.status == TaskStatus.PENDING else "🔄"

            print(f"{micro}{emoji} [{t['id']}] {t['name']} (~{task.remaining_minutes}m)")
            if t.get('project_name'):
                print(f"       📁 {t['project_name']}")
        print(f"{'─' * 60}")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _complete_task(self):
        """Completa un task."""
        task_id = self.input_number("ID del task da completare", 1, 99999, 1)
        task = self.db.get_task(task_id)

        if not task:
            self.print_error("Task non trovato")
            return

        self.db.complete_task(task_id)
        self.print_success(f"Task '{task['name']}' completato!")

        # Aggiorna stats giornaliere
        self.db.update_daily_stats(tasks_completed=1)

        points, achievements = self.gamification.on_task_completed(task)
        print(f"  {Colors.GREEN}+{points} punti!{Colors.RESET}")
        for ach in achievements:
            self._show_achievement_unlocked(ach)

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _split_task(self):
        """Spacchetta task in micro-task."""
        task_id = self.input_number("ID del task da spacchettare", 1, 99999, 1)
        task_data = self.db.get_task(task_id)

        if not task_data:
            self.print_error("Task non trovato")
            return

        task = Task.from_dict(task_data)

        print(f"\nSpacchettamento: {task.name}")
        print(f"\n{Colors.CYAN}Suggerimenti automatici:{Colors.RESET}")

        from core.task import TaskSuggestion
        task_type = TaskSuggestion.detect_task_type(task)
        suggestions = TaskSuggestion.suggest_micro_tasks(task, task_type)

        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s}")

        use_suggestions = self.input_prompt("\nUsare questi suggerimenti? (s/n)", "s")

        if use_suggestions.lower() == 's':
            task_ids = self.anti_proc.create_micro_tasks_in_db(task)
            self.print_success(f"Creati {len(task_ids)} micro-task!")
        else:
            print("\nInserisci i micro-task manualmente (uno per riga, riga vuota per finire):")
            micro_names = []
            while True:
                name = input(f"  {len(micro_names)+1}. ")
                if not name:
                    break
                micro_names.append(name)

            if micro_names:
                for i, name in enumerate(micro_names):
                    self.db.create_task(
                        name=name,
                        project_id=task.project_id,
                        is_micro_task=True,
                        parent_task_id=task.id,
                        order_index=i,
                        estimated_minutes=max(5, task.estimated_minutes // len(micro_names))
                    )
                self.print_success(f"Creati {len(micro_names)} micro-task!")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    # === ANTI-PROCRASTINATION ===

    def _anti_procrastination_menu(self):
        """Menu anti-procrastinazione."""
        self.clear_screen()
        self.print_header("💡 AIUTO ANTI-PROCRASTINAZIONE")

        print(self.anti_proc.get_motivation_message())
        print()

        options = [
            "🔍 Diagnostica il mio blocco",
            "🔬 Spacchetta un task",
            "🎯 Rituale di avvio",
            "💪 Commitment Device",
            "📝 Implementation Intention",
            "⬅️ Torna al menu"
        ]

        choice = self.input_choice("Cosa ti serve?", options)

        if choice == 0:
            self._diagnose_block()
        elif choice == 1:
            self._split_task()
        elif choice == 2:
            self._show_startup_ritual()
        elif choice == 3:
            self._create_commitment()
        elif choice == 4:
            self._create_intention()

    def _diagnose_block(self):
        """Diagnostica il blocco di procrastinazione."""
        print(f"\n{Colors.CYAN}Rispondi alle domande per capire cosa ti blocca:{Colors.RESET}\n")

        questions = self.anti_proc.ask_block_questions()
        detected_reason = None

        for question, reason in questions:
            answer = self.input_prompt(f"{question} (s/n)", "n")
            if answer.lower() == 's':
                detected_reason = reason
                break

        if not detected_reason:
            detected_reason = ProcrastinationReason.UNKNOWN

        intervention = self.anti_proc.get_intervention(detected_reason)

        print(f"\n{Colors.GREEN}{'═' * 50}{Colors.RESET}")
        print(f"{Colors.BOLD}Tecnica: {intervention.technique}{Colors.RESET}")
        print(f"\n{intervention.message}")
        print(f"\n{Colors.CYAN}Azione suggerita:{Colors.RESET}")
        print(f"  👉 {intervention.action}")
        print(f"{Colors.GREEN}{'═' * 50}{Colors.RESET}")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _show_startup_ritual(self):
        """Mostra il rituale di avvio."""
        print(f"\n{Colors.CYAN}🎯 RITUALE DI AVVIO{Colors.RESET}\n")

        for step in self.anti_proc.get_startup_ritual():
            print(f"  {step}")

        input(f"\n{Colors.DIM}Premi Invio quando sei pronto...{Colors.RESET}")

    def _create_commitment(self):
        """Crea un commitment device."""
        tasks = self.db.get_pending_tasks(limit=5)
        if not tasks:
            self.print_warning("Nessun task disponibile")
            return

        print("\nTask disponibili:")
        for i, t in enumerate(tasks, 1):
            print(f"  {i}. {t['name']}")

        choice = self.input_number("Seleziona task", 1, len(tasks), 1)
        task = Task.from_dict(tasks[choice - 1])

        commitment = self.anti_proc.get_commitment_device(task)

        print(f"\n{Colors.GREEN}{'═' * 50}{Colors.RESET}")
        print(f"{Colors.BOLD}📜 IL TUO IMPEGNO{Colors.RESET}")
        print(f"\n  \"{commitment['commitment']}\"")
        print(f"\n  ⏰ Inizio: {commitment['start_time']}")
        print(f"  🏁 Fine: {commitment['end_time']}")
        print(f"\n  🎁 Ricompensa: {commitment['reward']}")
        print(f"  ⚠️ Se non lo faccio: {commitment['consequence']}")
        print(f"{Colors.GREEN}{'═' * 50}{Colors.RESET}")

        input(f"\n{Colors.DIM}Premi Invio e inizia!{Colors.RESET}")

    def _create_intention(self):
        """Crea un implementation intention."""
        tasks = self.db.get_pending_tasks(limit=5)
        if not tasks:
            self.print_warning("Nessun task disponibile")
            return

        print("\nTask disponibili:")
        for i, t in enumerate(tasks, 1):
            print(f"  {i}. {t['name']}")

        choice = self.input_number("Seleziona task", 1, len(tasks), 1)
        task = Task.from_dict(tasks[choice - 1])

        intention = self.anti_proc.get_implementation_intention(task)

        print(f"\n{Colors.GREEN}{'═' * 50}{Colors.RESET}")
        print(f"{Colors.BOLD}🎯 LA TUA INTENZIONE{Colors.RESET}")
        print(f"\n  \"{intention}\"")
        print(f"\n{Colors.DIM}(Ripetila ad alta voce per renderla più potente){Colors.RESET}")
        print(f"{Colors.GREEN}{'═' * 50}{Colors.RESET}")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    # === STATS ===

    def _show_stats_menu(self):
        """Menu statistiche."""
        self.clear_screen()
        self.print_header("📊 STATISTICHE & ANALYTICS")

        options = [
            "📅 Sommario di oggi",
            "📈 Report settimanale",
            "📊 Report mensile",
            "💡 Insights",
            "⏰ Momento migliore per lavorare",
            "⬅️ Torna al menu"
        ]

        choice = self.input_choice("Cosa vuoi vedere?", options)

        if choice == 0:
            self._show_daily_summary()
        elif choice == 1:
            print(self.analytics.generate_weekly_report())
        elif choice == 2:
            self._show_monthly_summary()
        elif choice == 3:
            self._show_insights()
        elif choice == 4:
            self._show_best_time()

        if choice != 5:
            input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _show_daily_summary(self):
        """Mostra sommario giornaliero."""
        summary = self.analytics.get_daily_summary()

        print(f"\n{Colors.CYAN}📅 OGGI ({summary['date']}){Colors.RESET}")
        print(f"  ⏱️ Focus: {summary['focus_minutes']} min ({summary['focus_hours']}h)")
        print(f"  ✅ Task completati: {summary['tasks_completed']}")
        print(f"  ⭐ Punti guadagnati: {summary['points_earned']}")
        print(f"  🎯 Decisioni prese: {summary['decisions_made']}")
        print(f"  🍅 Sessioni: {summary['completed_sessions']}/{summary['total_sessions']}")
        print(f"  ⚡ Media interruzioni: {summary['avg_interruptions']}")

    def _show_monthly_summary(self):
        """Mostra sommario mensile."""
        summary = self.analytics.get_monthly_summary()

        print(f"\n{Colors.CYAN}📊 ULTIMI 30 GIORNI{Colors.RESET}")
        print(f"  ⏱️ Focus totale: {summary['total_focus_hours']}h")
        print(f"  ✅ Task completati: {summary['total_tasks_completed']}")
        print(f"  ⭐ Punti guadagnati: {summary['total_points_earned']}")
        print(f"  📅 Giorni attivi: {summary['active_days']}/30")
        print(f"  📈 Costanza: {summary['consistency_rate']}%")

    def _show_insights(self):
        """Mostra gli insights."""
        insights = self.analytics.get_insights()

        print(f"\n{Colors.CYAN}💡 INSIGHTS{Colors.RESET}\n")

        if not insights:
            print("  Nessun insight disponibile. Lavora di più!")
            return

        for insight in insights:
            print(f"  {insight['icon']} {Colors.BOLD}{insight['title']}{Colors.RESET}")
            print(f"     {insight['message']}")
            if insight.get('action'):
                print(f"     👉 {insight['action']}")
            print()

    def _show_best_time(self):
        """Mostra il momento migliore per lavorare."""
        analysis = self.analytics.get_best_time_to_work()

        print(f"\n{Colors.CYAN}⏰ ANALISI PRODUTTIVITÀ PER FASCIA ORARIA{Colors.RESET}\n")

        if 'message' in analysis:
            print(f"  {analysis['message']}")
            return

        print(f"  🏆 {analysis['recommendation']}\n")

        for slot, data in analysis.get('time_breakdown', {}).items():
            if data['sessions'] > 0:
                bar = "█" * int(data['completion_rate'] / 10)
                print(f"  {slot}")
                print(f"    Sessioni: {data['sessions']} | Completamento: {bar} {data['completion_rate']}%")

    # === PROFILE ===

    def _show_profile(self):
        """Mostra profilo e achievements."""
        self.clear_screen()

        print(self.gamification.generate_stats_display())
        print()
        print(self.gamification.generate_achievements_display())

        # Sfide giornaliere
        challenges = self.gamification.get_daily_challenges()
        print(f"\n{Colors.CYAN}🎯 SFIDE DI OGGI{Colors.RESET}")
        for c in challenges:
            status = "✅" if c['completed'] else f"{c['progress']:.0f}%"
            print(f"  {c['icon']} {c['name']}: {status} ({c['current']}/{c['goal']})")

        # Productivity score
        score, desc = self.analytics.get_productivity_score()
        print(f"\n{Colors.CYAN}📊 PRODUCTIVITY SCORE: {score}/100{Colors.RESET}")
        print(f"  {desc}")

        input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _show_achievement_unlocked(self, achievement):
        """Mostra notifica achievement sbloccato."""
        print(f"\n{Colors.YELLOW}{'═' * 40}{Colors.RESET}")
        print(f"  {Colors.BOLD}🏆 ACHIEVEMENT SBLOCCATO!{Colors.RESET}")
        print(f"  {achievement.icon} {achievement.name}")
        print(f"  {achievement.description}")
        print(f"  {Colors.GREEN}+{achievement.points} punti!{Colors.RESET}")
        print(f"{Colors.YELLOW}{'═' * 40}{Colors.RESET}\n")

    # === SETTINGS ===

    def _settings_menu(self):
        """Menu impostazioni."""
        self.clear_screen()
        self.print_header("⚙️ IMPOSTAZIONI")

        profile = self.db.get_user_profile()

        options = [
            "✏️ Cambia username",
            "🔄 Reset statistiche",
            "💾 Esporta dati",
            "⬅️ Torna al menu"
        ]

        choice = self.input_choice("Cosa vuoi fare?", options)

        if choice == 0:
            new_name = self.input_prompt("Nuovo username", profile.get('username', 'User'))
            self.db.update_user_profile(username=new_name)
            self.print_success(f"Username cambiato in '{new_name}'!")
        elif choice == 1:
            confirm = self.input_prompt("Sei sicuro? Questo cancellerà tutte le statistiche (s/n)", "n")
            if confirm.lower() == 's':
                # Reset semplificato - in produzione servirebbe più logica
                self.print_warning("Reset non implementato in questa versione")
        elif choice == 2:
            self.print_info(f"Database salvato in: {self.db.db_path}")

        if choice != 3:
            input(f"\n{Colors.DIM}Premi Invio per continuare...{Colors.RESET}")

    def _confirm_exit(self):
        """Conferma uscita."""
        confirm = self.input_prompt("Vuoi davvero uscire? (s/n)", "n")
        if confirm.lower() == 's':
            # Ferma eventuale sessione focus
            if self.focus_mode.current_session:
                self.focus_mode.stop_session(completed=False)

            print(f"\n{Colors.CYAN}Arrivederci! Continua a spaccare! 💪{Colors.RESET}\n")
            self.running = False
            self.db.close()
            sys.exit(0)


def main():
    """Entry point."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
