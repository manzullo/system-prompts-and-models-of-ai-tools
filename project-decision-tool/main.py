#!/usr/bin/env python3
"""
Project Decision Tool - Il tuo assistente per la produttività.

Aiuta a:
- Decidere su cosa lavorare
- Mantenere il focus con Pomodoro avanzato
- Combattere la procrastinazione
- Tracciare i progressi con gamification

Uso:
    python main.py              # Avvia l'interfaccia interattiva
    python main.py --help       # Mostra aiuto
    python main.py decide       # Raccomandazione rapida
    python main.py focus        # Inizia sessione focus
    python main.py stats        # Mostra statistiche
"""

import sys
import os

# Aggiungi la directory corrente al path per gli import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.interface import CLI, Colors


def print_banner():
    """Stampa il banner dell'applicazione."""
    print(f"""
{Colors.CYAN}
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🎯 PROJECT DECISION TOOL                                ║
    ║                                                           ║
    ║   Decidi. Focalizza. Conquista.                           ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
{Colors.RESET}
""")


def print_help():
    """Stampa l'aiuto."""
    print("""
Uso: python main.py [comando]

Comandi disponibili:
    (nessuno)     Avvia l'interfaccia interattiva
    decide        Ottieni una raccomandazione rapida
    focus         Inizia una sessione focus (Pomodoro)
    stats         Mostra le statistiche
    projects      Lista progetti attivi
    tasks         Lista task pending
    help          Mostra questo messaggio

Esempi:
    python main.py              # Interfaccia completa
    python main.py decide       # "Cosa dovrei fare adesso?"
    python main.py focus 25     # Pomodoro di 25 minuti

Per maggiori informazioni, visita la documentazione.
""")


def quick_decide():
    """Raccomandazione rapida da linea di comando."""
    from core.database import Database
    from core.decision_engine import DecisionEngine, DecisionMode

    db = Database()
    engine = DecisionEngine(db)

    print(f"\n{Colors.CYAN}🎯 Analizzando i tuoi progetti...{Colors.RESET}\n")

    rec = engine.get_recommendation(mode=DecisionMode.SMART)

    if rec.project or rec.task:
        name = rec.project.name if rec.project else rec.task.name
        print(f"  {Colors.GREEN}▶ RACCOMANDAZIONE:{Colors.RESET} {Colors.BOLD}{name}{Colors.RESET}")
        print()
        for reason in rec.reasoning[:3]:
            print(f"    • {reason}")
        print()
        print(f"  Confidence: {rec.confidence * 100:.0f}%")
    else:
        print("  Nessun progetto o task attivo. Creane uno nuovo!")

    db.close()


def quick_stats():
    """Statistiche rapide da linea di comando."""
    from core.database import Database
    from core.analytics import Analytics
    from core.gamification import GamificationSystem

    db = Database()
    analytics = Analytics(db)
    gamification = GamificationSystem(db)

    print(gamification.generate_stats_display())
    print()

    score, desc = analytics.get_productivity_score()
    print(f"  Productivity Score: {score}/100")
    print(f"  {desc}")

    db.close()


def quick_projects():
    """Lista progetti rapida."""
    from core.database import Database
    from core.project import Project

    db = Database()
    projects = db.get_all_projects(status='active')

    if not projects:
        print(f"\n  {Colors.YELLOW}Nessun progetto attivo.{Colors.RESET}")
        print("  Usa l'interfaccia interattiva per crearne uno.\n")
    else:
        print(f"\n{Colors.CYAN}📋 PROGETTI ATTIVI{Colors.RESET}\n")
        for p in projects:
            proj = Project.from_dict(p)
            print(f"  [{p['id']}] {Colors.BOLD}{p['name']}{Colors.RESET}")
            print(f"      I:{p['importance']} U:{p['urgency']} E:{p['excitement']} "
                  f"| {proj.progress:.0f}% | {proj.eisenhower_quadrant}")

    db.close()


def quick_tasks():
    """Lista task rapida."""
    from core.database import Database

    db = Database()
    tasks = db.get_pending_tasks(limit=10)

    if not tasks:
        print(f"\n  {Colors.YELLOW}Nessun task pending.{Colors.RESET}")
    else:
        print(f"\n{Colors.CYAN}✅ TASK PENDING{Colors.RESET}\n")
        for t in tasks:
            remaining = t['estimated_minutes'] - t['logged_minutes']
            project = f" ({t['project_name']})" if t.get('project_name') else ""
            print(f"  [{t['id']}] {t['name']}{project} ~{remaining}m")

    db.close()


def main():
    """Entry point principale."""
    args = sys.argv[1:]

    if not args:
        # Avvia interfaccia interattiva
        print_banner()
        cli = CLI()
        cli.run()
        return

    command = args[0].lower()

    if command in ['help', '-h', '--help']:
        print_help()
    elif command == 'decide':
        quick_decide()
    elif command == 'stats':
        quick_stats()
    elif command == 'projects':
        quick_projects()
    elif command == 'tasks':
        quick_tasks()
    elif command == 'focus':
        # Focus mode con durata opzionale
        duration = int(args[1]) if len(args) > 1 else 25
        print(f"\n{Colors.CYAN}⏱️ Avvio sessione focus di {duration} minuti...{Colors.RESET}")
        print("Usa l'interfaccia interattiva per la versione completa.\n")
        cli = CLI()
        cli._run_focus_session(duration=duration)
    else:
        print(f"{Colors.RED}Comando non riconosciuto: {command}{Colors.RESET}")
        print("Usa 'python main.py help' per vedere i comandi disponibili.")


if __name__ == "__main__":
    main()
