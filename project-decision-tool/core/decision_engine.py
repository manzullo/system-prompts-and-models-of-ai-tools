"""
Decision Engine - Il cuore del sistema.
Aiuta l'utente a decidere su cosa lavorare basandosi su molteplici fattori.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .database import Database
from .project import Project, ProjectStatus, EnergyLevel
from .task import Task, TaskStatus


class DecisionMode(Enum):
    """Modalità di decisione disponibili."""
    SMART = "smart"           # Algoritmo completo
    URGENT = "urgent"         # Solo urgenza/deadline
    ENERGY_MATCH = "energy"   # Match con energia attuale
    QUICK_WINS = "quick"      # Task veloci per momentum
    RANDOM_TOP3 = "random"    # Scelta random tra i top 3
    EISENHOWER = "eisenhower" # Matrice Eisenhower pura


@dataclass
class DecisionContext:
    """Contesto per prendere una decisione."""
    current_energy: EnergyLevel = EnergyLevel.MEDIUM
    available_minutes: int = 60
    mood: int = 5  # 1-10
    time_of_day: str = "morning"  # morning, afternoon, evening, night
    already_worked_minutes: int = 0
    prefer_new: bool = False  # Preferire progetti nuovi vs quasi finiti


@dataclass
class Recommendation:
    """Una raccomandazione del Decision Engine."""
    project: Optional[Project] = None
    task: Optional[Task] = None
    score: float = 0.0
    reasoning: List[str] = None
    alternatives: List['Recommendation'] = None
    confidence: float = 0.0  # 0-1

    def __post_init__(self):
        if self.reasoning is None:
            self.reasoning = []
        if self.alternatives is None:
            self.alternatives = []


class DecisionEngine:
    """
    Motore decisionale che analizza progetti e task
    per raccomandare su cosa lavorare.
    """

    def __init__(self, db: Database):
        self.db = db

    def get_recommendation(self,
                          context: DecisionContext = None,
                          mode: DecisionMode = DecisionMode.SMART) -> Recommendation:
        """
        Ottiene una raccomandazione su cosa fare adesso.
        """
        if context is None:
            context = self._auto_detect_context()

        # Ottieni progetti e task attivi
        projects = self._get_active_projects()
        tasks = self._get_pending_tasks()

        if not projects and not tasks:
            return Recommendation(
                reasoning=["Non hai progetti o task attivi. Creane uno nuovo!"],
                confidence=1.0
            )

        # Calcola scores basati sulla modalità
        if mode == DecisionMode.SMART:
            return self._smart_recommendation(projects, tasks, context)
        elif mode == DecisionMode.URGENT:
            return self._urgent_recommendation(projects, tasks, context)
        elif mode == DecisionMode.ENERGY_MATCH:
            return self._energy_match_recommendation(projects, tasks, context)
        elif mode == DecisionMode.QUICK_WINS:
            return self._quick_wins_recommendation(tasks, context)
        elif mode == DecisionMode.RANDOM_TOP3:
            return self._random_top3_recommendation(projects, tasks, context)
        elif mode == DecisionMode.EISENHOWER:
            return self._eisenhower_recommendation(projects, context)

        return self._smart_recommendation(projects, tasks, context)

    def _auto_detect_context(self) -> DecisionContext:
        """Rileva automaticamente il contesto attuale."""
        now = datetime.now()
        hour = now.hour

        # Determina momento della giornata
        if 5 <= hour < 12:
            time_of_day = "morning"
            # Mattina: di solito più energia
            default_energy = EnergyLevel.HIGH
        elif 12 <= hour < 14:
            time_of_day = "afternoon"
            # Post pranzo: energia media-bassa
            default_energy = EnergyLevel.MEDIUM
        elif 14 <= hour < 18:
            time_of_day = "afternoon"
            default_energy = EnergyLevel.MEDIUM
        elif 18 <= hour < 22:
            time_of_day = "evening"
            default_energy = EnergyLevel.LOW
        else:
            time_of_day = "night"
            default_energy = EnergyLevel.LOW

        # Calcola minuti già lavorati oggi
        today = now.strftime('%Y-%m-%d')
        sessions = self.db.get_focus_sessions(date=today)
        worked_minutes = sum(s['duration_minutes'] for s in sessions if s['completed'])

        return DecisionContext(
            current_energy=default_energy,
            available_minutes=60,
            mood=5,
            time_of_day=time_of_day,
            already_worked_minutes=worked_minutes
        )

    def _get_active_projects(self) -> List[Project]:
        """Ottiene progetti attivi come oggetti Project."""
        raw_projects = self.db.get_all_projects(status='active')
        return [Project.from_dict(p) for p in raw_projects]

    def _get_pending_tasks(self) -> List[Task]:
        """Ottiene task pending come oggetti Task."""
        raw_tasks = self.db.get_pending_tasks()
        return [Task.from_dict(t) for t in raw_tasks]

    def _smart_recommendation(self, projects: List[Project],
                             tasks: List[Task],
                             context: DecisionContext) -> Recommendation:
        """
        Raccomandazione intelligente che bilancia tutti i fattori.
        """
        scored_items = []
        reasoning = []

        # Score progetti
        for project in projects:
            score = self._calculate_smart_score(project, None, context)
            scored_items.append(('project', project, None, score))

        # Score task (con bonus se associati a progetti importanti)
        for task in tasks:
            # Trova il progetto associato se esiste
            project = None
            if task.project_id:
                project = next((p for p in projects if p.id == task.project_id), None)

            score = self._calculate_smart_score(project, task, context)
            scored_items.append(('task', project, task, score))

        if not scored_items:
            return Recommendation(
                reasoning=["Nessun elemento da valutare"],
                confidence=0.0
            )

        # Ordina per score
        scored_items.sort(key=lambda x: x[3], reverse=True)

        # Prendi il migliore
        best_type, best_project, best_task, best_score = scored_items[0]

        # Calcola confidence basata sulla differenza con il secondo
        confidence = 0.7
        if len(scored_items) > 1:
            second_score = scored_items[1][3]
            if best_score > 0:
                diff_ratio = (best_score - second_score) / best_score
                confidence = min(0.95, 0.5 + diff_ratio * 0.5)

        # Costruisci reasoning
        reasoning = self._build_reasoning(best_project, best_task, context, best_score)

        # Alternative (top 3 escluso il primo)
        alternatives = []
        for i, (item_type, proj, task, score) in enumerate(scored_items[1:4]):
            alt = Recommendation(
                project=proj,
                task=task,
                score=score,
                reasoning=[f"Score: {score:.1f}"]
            )
            alternatives.append(alt)

        # Log della decisione
        if best_project:
            alt_names = [f"{a.project.name if a.project else a.task.name}" for a in alternatives]
            self.db.log_decision(
                decision_type='smart',
                chosen_project_id=best_project.id if best_project else None,
                alternatives=', '.join(alt_names),
                reasoning='; '.join(reasoning)
            )

        return Recommendation(
            project=best_project,
            task=best_task,
            score=best_score,
            reasoning=reasoning,
            alternatives=alternatives,
            confidence=confidence
        )

    def _calculate_smart_score(self, project: Optional[Project],
                               task: Optional[Task],
                               context: DecisionContext) -> float:
        """Calcola lo score combinato per progetto/task."""
        score = 0.0

        # === SCORE BASE DA PROGETTO ===
        if project:
            # Importanza e Urgenza (peso principale)
            score += project.importance * 3.0
            score += project.urgency * 2.5

            # Entusiasmo (anti-procrastinazione)
            score += project.excitement * 2.0

            # Deadline
            days = project.days_until_deadline
            if days is not None:
                if days < 0:
                    score += 25  # OVERDUE!
                elif days == 0:
                    score += 20
                elif days <= 2:
                    score += 15
                elif days <= 7:
                    score += 8

            # Progresso (preferire progetti quasi finiti)
            if project.progress >= 80:
                score += 10  # "Finiscilo!"
            elif project.progress >= 50:
                score += 5

            # Match energia
            score += self._energy_match_bonus(project.energy_required, context.current_energy)

        # === SCORE DA TASK ===
        if task:
            score += task.priority * 1.5

            # Quick win bonus
            if task.remaining_minutes <= 15:
                score += 12
            elif task.remaining_minutes <= 30:
                score += 6

            # Micro-task bonus (più facile iniziare)
            if task.is_micro_task:
                score += 8

            # Match energia
            score += self._energy_match_bonus(task.energy_required, context.current_energy)

            # Overdue
            if task.is_overdue:
                score += 15

        # === FATTORI CONTESTUALI ===

        # Momento della giornata
        if context.time_of_day == "morning" and project:
            # Mattina: preferire task impegnativi
            if project.energy_required in [EnergyLevel.HIGH, EnergyLevel.EXTREME]:
                score += 5
        elif context.time_of_day in ["evening", "night"]:
            # Sera: preferire task leggeri
            if project and project.energy_required == EnergyLevel.LOW:
                score += 5
            if task and task.is_quick_win:
                score += 3

        # Già lavorato tanto oggi? Preferisci cose leggere
        if context.already_worked_minutes > 240:  # 4+ ore
            if task and task.is_quick_win:
                score += 5

        # Mood basso? Preferisci cose che ti entusiasmano
        if context.mood < 5 and project:
            score += project.excitement * 0.5

        return max(0, score)

    def _energy_match_bonus(self, required: EnergyLevel, current: EnergyLevel) -> float:
        """Calcola bonus/malus per match energia."""
        levels = {
            EnergyLevel.LOW: 1,
            EnergyLevel.MEDIUM: 2,
            EnergyLevel.HIGH: 3,
            EnergyLevel.EXTREME: 4
        }

        current_val = levels.get(current, 2)
        required_val = levels.get(required, 2)

        if current_val >= required_val:
            # Hai abbastanza energia
            if current_val == required_val:
                return 8  # Match perfetto
            return 5
        else:
            # Non abbastanza energia - penalità
            return -(required_val - current_val) * 5

    def _build_reasoning(self, project: Optional[Project],
                        task: Optional[Task],
                        context: DecisionContext,
                        score: float) -> List[str]:
        """Costruisce spiegazione della raccomandazione."""
        reasons = []

        if project:
            reasons.append(f"📊 Score totale: {score:.1f}")

            # Quadrante Eisenhower
            quadrant = project.eisenhower_quadrant
            quadrant_msgs = {
                "DO": "⚡ URGENTE e IMPORTANTE - Fallo subito!",
                "SCHEDULE": "📅 Importante ma non urgente - Pianifica",
                "DELEGATE": "👥 Urgente ma poco importante - Considera delegare",
                "ELIMINATE": "🗑️ Né urgente né importante - Valuta se eliminare"
            }
            reasons.append(quadrant_msgs.get(quadrant, ""))

            # Deadline
            days = project.days_until_deadline
            if days is not None:
                if days < 0:
                    reasons.append(f"🚨 IN RITARDO di {abs(days)} giorni!")
                elif days == 0:
                    reasons.append("⏰ Scade OGGI!")
                elif days <= 3:
                    reasons.append(f"⚠️ Scade tra {days} giorni")

            # Energia
            energy_emoji = {
                EnergyLevel.LOW: "🔋",
                EnergyLevel.MEDIUM: "🔋🔋",
                EnergyLevel.HIGH: "🔋🔋🔋",
                EnergyLevel.EXTREME: "⚡⚡⚡"
            }
            if project.energy_required == context.current_energy:
                reasons.append(f"{energy_emoji.get(project.energy_required, '')} Energia perfetta per questo task!")

            # Progresso
            if project.progress >= 80:
                reasons.append(f"🏁 Quasi finito ({project.progress:.0f}%) - concludilo!")
            elif project.progress >= 50:
                reasons.append(f"📈 Buon progresso ({project.progress:.0f}%)")

            # Entusiasmo
            if project.excitement >= 8:
                reasons.append("🔥 Questo progetto ti entusiasma!")

        if task:
            if task.is_quick_win:
                reasons.append(f"⚡ Quick win! Solo ~{task.remaining_minutes} minuti")

            if task.is_micro_task:
                reasons.append("🎯 Micro-task: facile da iniziare")

        # Contestuali
        if context.time_of_day == "morning":
            reasons.append("🌅 Mattina: momento ideale per task impegnativi")
        elif context.time_of_day == "evening":
            reasons.append("🌙 Sera: preferisci task leggeri")

        return reasons

    def _urgent_recommendation(self, projects: List[Project],
                               tasks: List[Task],
                               context: DecisionContext) -> Recommendation:
        """Solo urgenza e deadline."""
        urgent_projects = sorted(
            [p for p in projects if p.deadline],
            key=lambda p: p.deadline
        )

        if not urgent_projects:
            # Fallback su urgency score
            urgent_projects = sorted(projects, key=lambda p: p.urgency, reverse=True)

        if urgent_projects:
            best = urgent_projects[0]
            return Recommendation(
                project=best,
                score=100,
                reasoning=[f"🚨 Deadline più vicina: {best.deadline}" if best.deadline else "Alta urgenza"],
                confidence=0.9
            )

        return Recommendation(reasoning=["Nessun progetto urgente"])

    def _energy_match_recommendation(self, projects: List[Project],
                                     tasks: List[Task],
                                     context: DecisionContext) -> Recommendation:
        """Match basato sull'energia attuale."""
        matching = [p for p in projects if p.energy_required == context.current_energy]

        if matching:
            best = max(matching, key=lambda p: p.importance)
            return Recommendation(
                project=best,
                score=80,
                reasoning=[f"🔋 Match perfetto con la tua energia attuale ({context.current_energy.value})"],
                confidence=0.85
            )

        # Fallback: progetti con energia richiesta <= attuale
        energy_order = [EnergyLevel.LOW, EnergyLevel.MEDIUM, EnergyLevel.HIGH, EnergyLevel.EXTREME]
        current_idx = energy_order.index(context.current_energy)

        doable = [p for p in projects
                  if energy_order.index(p.energy_required) <= current_idx]

        if doable:
            best = max(doable, key=lambda p: p.importance)
            return Recommendation(
                project=best,
                score=60,
                reasoning=["Hai abbastanza energia per questo"],
                confidence=0.7
            )

        return Recommendation(reasoning=["Nessun match energia trovato"])

    def _quick_wins_recommendation(self, tasks: List[Task],
                                   context: DecisionContext) -> Recommendation:
        """Task veloci per costruire momentum."""
        quick_tasks = [t for t in tasks if t.remaining_minutes <= 15]

        if quick_tasks:
            # Ordina per priorità
            best = max(quick_tasks, key=lambda t: t.priority)
            return Recommendation(
                task=best,
                score=90,
                reasoning=[
                    f"⚡ Quick win: {best.remaining_minutes} minuti",
                    "🚀 Perfetto per costruire momentum!"
                ],
                confidence=0.9
            )

        # Fallback: task più brevi disponibili
        if tasks:
            shortest = min(tasks, key=lambda t: t.remaining_minutes)
            return Recommendation(
                task=shortest,
                score=50,
                reasoning=[f"Il task più breve disponibile ({shortest.remaining_minutes}m)"],
                confidence=0.6
            )

        return Recommendation(reasoning=["Nessun task disponibile"])

    def _random_top3_recommendation(self, projects: List[Project],
                                    tasks: List[Task],
                                    context: DecisionContext) -> Recommendation:
        """Scelta casuale tra i top 3 (riduce paralisi decisionale)."""
        # Prima ottieni smart recommendation per avere i top 3
        smart = self._smart_recommendation(projects, tasks, context)

        candidates = [smart]
        candidates.extend(smart.alternatives[:2])

        # Filtra None
        valid_candidates = [c for c in candidates if c.project or c.task]

        if valid_candidates:
            chosen = random.choice(valid_candidates)
            chosen.reasoning = [
                "🎲 Scelto casualmente tra i migliori 3",
                "Questo elimina la paralisi decisionale!"
            ] + chosen.reasoning
            chosen.confidence = 0.7
            return chosen

        return smart

    def _eisenhower_recommendation(self, projects: List[Project],
                                   context: DecisionContext) -> Recommendation:
        """Pura matrice di Eisenhower."""
        # Raggruppa per quadrante
        quadrants = {"DO": [], "SCHEDULE": [], "DELEGATE": [], "ELIMINATE": []}

        for p in projects:
            q = p.eisenhower_quadrant
            quadrants[q].append(p)

        # Priorità: DO > SCHEDULE > DELEGATE > ELIMINATE
        for quadrant in ["DO", "SCHEDULE", "DELEGATE", "ELIMINATE"]:
            if quadrants[quadrant]:
                # Prendi quello con più excitement nel quadrante
                best = max(quadrants[quadrant], key=lambda p: p.excitement)

                quadrant_advice = {
                    "DO": "⚡ Urgente E Importante - FALLO ORA!",
                    "SCHEDULE": "📅 Importante - Pianifica tempo dedicato",
                    "DELEGATE": "👥 Urgente ma meno importante - Delega se puoi",
                    "ELIMINATE": "🤔 Valuta se eliminare questo progetto"
                }

                return Recommendation(
                    project=best,
                    score=100 if quadrant == "DO" else 70,
                    reasoning=[
                        f"📊 Matrice Eisenhower: {quadrant}",
                        quadrant_advice[quadrant]
                    ],
                    confidence=0.85
                )

        return Recommendation(reasoning=["Nessun progetto da valutare"])

    def ask_clarifying_questions(self) -> List[Tuple[str, List[str]]]:
        """
        Genera domande per raffinare il contesto.
        Ritorna lista di (domanda, opzioni_risposta).
        """
        return [
            ("Come ti senti in termini di energia?",
             ["🔋 Bassa", "🔋🔋 Media", "🔋🔋🔋 Alta", "⚡ Al massimo!"]),

            ("Quanto tempo hai a disposizione?",
             ["15 min", "30 min", "1 ora", "2+ ore"]),

            ("Qual è il tuo mood?",
             ["😫 Stanco/demotivato", "😐 Neutro", "😊 Bene", "🔥 Carico!"]),

            ("Preferisci...",
             ["🎯 Finire qualcosa di iniziato",
              "🆕 Iniziare qualcosa di nuovo",
              "⚡ Vittorie veloci",
              "🤔 Lascia decidere a me"])
        ]

    def should_take_break(self, context: DecisionContext) -> Tuple[bool, str]:
        """Consiglia se è ora di fare una pausa."""
        if context.already_worked_minutes >= 90:
            return True, "☕ Hai lavorato 90+ minuti. Fai una pausa di 15-20 min!"

        if context.already_worked_minutes >= 50 and context.mood < 4:
            return True, "😴 Mood basso dopo 50+ min di lavoro. Pausa consigliata!"

        return False, ""

    def get_daily_focus_suggestion(self) -> Dict[str, any]:
        """
        Suggerisce su cosa concentrarsi oggi.
        Analizza progetti e restituisce un piano giornaliero.
        """
        projects = self._get_active_projects()
        tasks = self._get_pending_tasks()

        # Trova il progetto "stella" del giorno
        if projects:
            star_project = max(
                projects,
                key=lambda p: p.importance * 2 + p.urgency + p.excitement
            )
        else:
            star_project = None

        # Quick wins per iniziare
        quick_wins = [t for t in tasks if t.remaining_minutes <= 15][:3]

        # Task più importante
        main_task = max(tasks, key=lambda t: t.priority) if tasks else None

        return {
            "star_project": star_project,
            "quick_wins": quick_wins,
            "main_task": main_task,
            "total_tasks": len(tasks),
            "total_projects": len(projects),
            "suggestion": self._generate_daily_plan_text(star_project, quick_wins, main_task)
        }

    def _generate_daily_plan_text(self, star: Optional[Project],
                                  quick_wins: List[Task],
                                  main_task: Optional[Task]) -> str:
        """Genera testo del piano giornaliero."""
        lines = ["📋 PIANO DI OGGI", "=" * 30, ""]

        if quick_wins:
            lines.append("🚀 INIZIA CON (Quick Wins):")
            for i, t in enumerate(quick_wins, 1):
                lines.append(f"   {i}. {t.name} (~{t.remaining_minutes}m)")
            lines.append("")

        if star:
            lines.append(f"⭐ PROGETTO PRINCIPALE: {star.name}")
            lines.append(f"   Importanza: {'⭐' * star.importance}")
            if star.deadline:
                lines.append(f"   Deadline: {star.deadline.strftime('%d/%m/%Y')}")
            lines.append("")

        if main_task and main_task not in quick_wins:
            lines.append(f"🎯 TASK PRIORITARIO: {main_task.name}")
            if main_task.project_name:
                lines.append(f"   (Progetto: {main_task.project_name})")
            lines.append("")

        lines.append("💡 CONSIGLIO: Inizia con un quick win per prendere slancio!")

        return "\n".join(lines)
