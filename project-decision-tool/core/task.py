"""
Modello Task - Rappresenta un task con supporto per micro-task.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from .project import EnergyLevel


class TaskStatus(Enum):
    """Stati possibili di un task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class Task:
    """Rappresenta un task, possibilmente con micro-task figli."""

    id: Optional[int] = None
    project_id: Optional[int] = None
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1-10

    # Temporali
    estimated_minutes: int = 25  # Default: 1 pomodoro
    logged_minutes: int = 0
    due_date: Optional[datetime] = None

    # Energia
    energy_required: EnergyLevel = EnergyLevel.MEDIUM

    # Micro-task support
    is_micro_task: bool = False
    parent_task_id: Optional[int] = None
    order_index: int = 0

    # Metadata
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Non persistiti - popolati a runtime
    project_name: Optional[str] = None
    micro_tasks: List['Task'] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """Crea un Task da un dizionario."""
        task = cls()
        task.id = data.get('id')
        task.project_id = data.get('project_id')
        task.name = data.get('name', '')
        task.description = data.get('description', '')

        status_str = data.get('status', 'pending')
        task.status = TaskStatus(status_str) if isinstance(status_str, str) else status_str

        task.priority = data.get('priority', 5)
        task.estimated_minutes = data.get('estimated_minutes', 25)
        task.logged_minutes = data.get('logged_minutes', 0)

        due_date = data.get('due_date')
        if due_date and isinstance(due_date, str):
            try:
                task.due_date = datetime.fromisoformat(due_date)
            except:
                task.due_date = None

        energy_str = data.get('energy_required', 'medium')
        task.energy_required = EnergyLevel(energy_str) if isinstance(energy_str, str) else energy_str

        task.is_micro_task = bool(data.get('is_micro_task', False))
        task.parent_task_id = data.get('parent_task_id')
        task.order_index = data.get('order_index', 0)

        for date_field in ['created_at', 'completed_at']:
            value = data.get(date_field)
            if value and isinstance(value, str):
                try:
                    setattr(task, date_field, datetime.fromisoformat(value))
                except:
                    setattr(task, date_field, None)

        task.project_name = data.get('project_name')

        return task

    def to_dict(self) -> dict:
        """Converte il task in dizionario."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value if isinstance(self.status, TaskStatus) else self.status,
            'priority': self.priority,
            'estimated_minutes': self.estimated_minutes,
            'logged_minutes': self.logged_minutes,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'energy_required': self.energy_required.value if isinstance(self.energy_required, EnergyLevel) else self.energy_required,
            'is_micro_task': self.is_micro_task,
            'parent_task_id': self.parent_task_id,
            'order_index': self.order_index,
        }

    @property
    def is_quick_win(self) -> bool:
        """Task veloce da completare (< 15 min)."""
        remaining = self.estimated_minutes - self.logged_minutes
        return remaining <= 15

    @property
    def is_overdue(self) -> bool:
        """Verifica se il task è scaduto."""
        if not self.due_date:
            return False
        return datetime.now() > self.due_date and self.status == TaskStatus.PENDING

    @property
    def progress(self) -> float:
        """Percentuale di completamento basata sui minuti."""
        if self.estimated_minutes <= 0:
            return 0.0
        return min(100.0, (self.logged_minutes / self.estimated_minutes) * 100)

    @property
    def remaining_minutes(self) -> int:
        """Minuti rimanenti stimati."""
        return max(0, self.estimated_minutes - self.logged_minutes)

    def calculate_score(self, current_energy: EnergyLevel = EnergyLevel.MEDIUM) -> float:
        """
        Calcola uno score per ordinare i task.
        Usato dal Decision Engine per raccomandare il prossimo task.
        """
        score = 0.0

        # Base priorità
        score += self.priority * 2.0

        # Bonus quick wins (combatte la procrastinazione)
        if self.is_quick_win:
            score += 10

        # Bonus overdue
        if self.is_overdue:
            score += 15

        # Match energia
        energy_levels = {
            EnergyLevel.LOW: 1,
            EnergyLevel.MEDIUM: 2,
            EnergyLevel.HIGH: 3,
            EnergyLevel.EXTREME: 4
        }

        current_level = energy_levels.get(current_energy, 2)
        required_level = energy_levels.get(self.energy_required, 2)

        if current_level >= required_level:
            score += 5
        else:
            score -= (required_level - current_level) * 3

        # Bonus micro-task (più facili da iniziare)
        if self.is_micro_task:
            score += 8

        # Bonus task quasi completati
        if 70 <= self.progress < 100:
            score += 5

        return score

    def split_into_micro_tasks(self, descriptions: List[str]) -> List['Task']:
        """
        Crea micro-task da questo task.
        Ritorna lista di Task da salvare nel database.
        """
        micro_tasks = []

        total_time = self.estimated_minutes
        time_per_micro = max(5, total_time // len(descriptions))

        for i, desc in enumerate(descriptions):
            micro = Task(
                project_id=self.project_id,
                name=desc,
                description=f"Parte di: {self.name}",
                priority=self.priority,
                estimated_minutes=time_per_micro,
                energy_required=self.energy_required,
                is_micro_task=True,
                parent_task_id=self.id,
                order_index=i
            )
            micro_tasks.append(micro)

        return micro_tasks

    def __str__(self) -> str:
        status_emoji = {
            TaskStatus.PENDING: "⬜",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.BLOCKED: "🚫",
            TaskStatus.SKIPPED: "⏭️"
        }
        emoji = status_emoji.get(self.status, "")

        micro_indicator = "  └─" if self.is_micro_task else ""
        time_str = f"~{self.remaining_minutes}m" if self.remaining_minutes > 0 else "done"

        return f"{micro_indicator}{emoji} {self.name} ({time_str})"


class TaskSuggestion:
    """Suggerimento anti-procrastinazione per spacchettare un task."""

    TEMPLATES = {
        "generic": [
            "Definisci esattamente cosa vuoi ottenere",
            "Raccogli tutto il materiale necessario",
            "Crea l'ambiente di lavoro ideale",
            "Fai la prima azione più piccola possibile",
            "Rivedi e sistema quello che hai fatto"
        ],
        "coding": [
            "Leggi e comprendi il codice esistente",
            "Scrivi un test per il comportamento atteso",
            "Implementa la versione più semplice",
            "Refactoring e pulizia codice",
            "Documenta le modifiche"
        ],
        "writing": [
            "Fai brainstorming delle idee principali",
            "Crea uno schema/outline",
            "Scrivi la prima bozza senza editare",
            "Rivedi e migliora la struttura",
            "Editing finale e formattazione"
        ],
        "learning": [
            "Trova le risorse migliori (tutorial, docs)",
            "Leggi/guarda il materiale una volta",
            "Prendi appunti sui concetti chiave",
            "Pratica con un esercizio semplice",
            "Applica a un progetto reale"
        ],
        "planning": [
            "Definisci l'obiettivo finale chiaramente",
            "Identifica i vincoli e le risorse",
            "Elenca tutti i passaggi necessari",
            "Ordina per priorità e dipendenze",
            "Crea timeline e milestones"
        ],
        "creative": [
            "Ispirati con esempi e riferimenti",
            "Brainstorm senza giudizio",
            "Scegli l'idea migliore",
            "Crea un prototipo veloce",
            "Itera e migliora"
        ]
    }

    @classmethod
    def suggest_micro_tasks(cls, task: Task, task_type: str = "generic") -> List[str]:
        """Suggerisce micro-task basati sul tipo di task."""
        template = cls.TEMPLATES.get(task_type, cls.TEMPLATES["generic"])

        # Personalizza con il nome del task
        suggestions = []
        for step in template:
            personalized = f"{step} per '{task.name}'"
            suggestions.append(personalized)

        return suggestions

    @classmethod
    def detect_task_type(cls, task: Task) -> str:
        """Cerca di indovinare il tipo di task dal nome/descrizione."""
        text = f"{task.name} {task.description}".lower()

        coding_keywords = ['codice', 'code', 'bug', 'feature', 'api', 'database',
                          'fix', 'implement', 'refactor', 'test', 'deploy']
        writing_keywords = ['scrivi', 'write', 'articolo', 'blog', 'email',
                           'documento', 'report', 'testo']
        learning_keywords = ['impara', 'learn', 'studio', 'study', 'corso',
                            'tutorial', 'leggi', 'read']
        planning_keywords = ['pianifica', 'plan', 'organizza', 'schedule',
                            'strategia', 'roadmap', 'progetto']
        creative_keywords = ['design', 'crea', 'create', 'idea', 'concept',
                            'grafica', 'video', 'musica']

        if any(kw in text for kw in coding_keywords):
            return "coding"
        if any(kw in text for kw in writing_keywords):
            return "writing"
        if any(kw in text for kw in learning_keywords):
            return "learning"
        if any(kw in text for kw in planning_keywords):
            return "planning"
        if any(kw in text for kw in creative_keywords):
            return "creative"

        return "generic"
