"""
Modello Project - Rappresenta un progetto con tutte le sue proprietà.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


class ProjectStatus(Enum):
    """Stati possibili di un progetto."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class EnergyLevel(Enum):
    """Livelli di energia richiesta."""
    LOW = "low"          # Task leggeri, routine
    MEDIUM = "medium"    # Task standard
    HIGH = "high"        # Task impegnativi, creativi
    EXTREME = "extreme"  # Task che richiedono massima concentrazione


@dataclass
class Project:
    """Rappresenta un progetto con tutte le sue metriche."""

    id: Optional[int] = None
    name: str = ""
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    priority: int = 5  # 1-10

    # Temporali
    deadline: Optional[datetime] = None
    estimated_hours: float = 0.0
    logged_hours: float = 0.0

    # Metriche per Decision Engine
    energy_required: EnergyLevel = EnergyLevel.MEDIUM
    importance: int = 5  # 1-10 (Matrice Eisenhower)
    urgency: int = 5     # 1-10 (Matrice Eisenhower)
    excitement: int = 5  # 1-10 (quanto ti entusiasma)

    # Metadata
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        """Crea un Project da un dizionario (es. da database)."""
        project = cls()
        project.id = data.get('id')
        project.name = data.get('name', '')
        project.description = data.get('description', '')

        status_str = data.get('status', 'active')
        project.status = ProjectStatus(status_str) if isinstance(status_str, str) else status_str

        project.priority = data.get('priority', 5)

        deadline = data.get('deadline')
        if deadline and isinstance(deadline, str):
            try:
                project.deadline = datetime.fromisoformat(deadline)
            except:
                project.deadline = None
        else:
            project.deadline = deadline

        project.estimated_hours = data.get('estimated_hours', 0.0)
        project.logged_hours = data.get('logged_hours', 0.0)

        energy_str = data.get('energy_required', 'medium')
        project.energy_required = EnergyLevel(energy_str) if isinstance(energy_str, str) else energy_str

        project.importance = data.get('importance', 5)
        project.urgency = data.get('urgency', 5)
        project.excitement = data.get('excitement', 5)

        tags = data.get('tags', '')
        project.tags = tags.split(',') if isinstance(tags, str) and tags else []

        for date_field in ['created_at', 'updated_at', 'completed_at']:
            value = data.get(date_field)
            if value and isinstance(value, str):
                try:
                    setattr(project, date_field, datetime.fromisoformat(value))
                except:
                    setattr(project, date_field, None)

        return project

    def to_dict(self) -> dict:
        """Converte il progetto in dizionario per il database."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value if isinstance(self.status, ProjectStatus) else self.status,
            'priority': self.priority,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'estimated_hours': self.estimated_hours,
            'logged_hours': self.logged_hours,
            'energy_required': self.energy_required.value if isinstance(self.energy_required, EnergyLevel) else self.energy_required,
            'importance': self.importance,
            'urgency': self.urgency,
            'excitement': self.excitement,
            'tags': ','.join(self.tags) if self.tags else '',
        }

    @property
    def progress(self) -> float:
        """Calcola la percentuale di progresso basata sulle ore."""
        if self.estimated_hours <= 0:
            return 0.0
        return min(100.0, (self.logged_hours / self.estimated_hours) * 100)

    @property
    def is_overdue(self) -> bool:
        """Verifica se il progetto è in ritardo."""
        if not self.deadline:
            return False
        return datetime.now() > self.deadline and self.status == ProjectStatus.ACTIVE

    @property
    def days_until_deadline(self) -> Optional[int]:
        """Giorni rimanenti alla deadline."""
        if not self.deadline:
            return None
        delta = self.deadline - datetime.now()
        return delta.days

    @property
    def eisenhower_quadrant(self) -> str:
        """Determina il quadrante Eisenhower."""
        is_important = self.importance >= 7
        is_urgent = self.urgency >= 7

        if is_important and is_urgent:
            return "DO"      # Fai subito
        elif is_important and not is_urgent:
            return "SCHEDULE"  # Pianifica
        elif not is_important and is_urgent:
            return "DELEGATE"  # Delega se possibile
        else:
            return "ELIMINATE"  # Elimina o rimanda

    def calculate_score(self, current_energy: EnergyLevel = EnergyLevel.MEDIUM,
                       time_available_minutes: int = 60) -> float:
        """
        Calcola uno score complessivo per il Decision Engine.
        Score più alto = progetto più adatto da fare ora.
        """
        score = 0.0

        # Base: importanza e urgenza (peso maggiore)
        score += self.importance * 3.0
        score += self.urgency * 2.5

        # Bonus entusiasmo (combatte la procrastinazione)
        score += self.excitement * 1.5

        # Bonus deadline imminente
        if self.days_until_deadline is not None:
            if self.days_until_deadline < 0:
                score += 20  # Overdue - priorità massima
            elif self.days_until_deadline <= 1:
                score += 15
            elif self.days_until_deadline <= 3:
                score += 10
            elif self.days_until_deadline <= 7:
                score += 5

        # Match energia
        energy_levels = {
            EnergyLevel.LOW: 1,
            EnergyLevel.MEDIUM: 2,
            EnergyLevel.HIGH: 3,
            EnergyLevel.EXTREME: 4
        }

        current_level = energy_levels.get(current_energy, 2)
        required_level = energy_levels.get(self.energy_required, 2)

        # Bonus se l'energia richiesta corrisponde
        if current_level >= required_level:
            score += 8
        else:
            # Penalità se non hai abbastanza energia
            score -= (required_level - current_level) * 5

        # Bonus progresso (preferire progetti quasi completati)
        if 70 <= self.progress < 100:
            score += 7

        # Penalità se non hai tempo (stima)
        hours_remaining = self.estimated_hours - self.logged_hours
        if hours_remaining > 0 and time_available_minutes < 30:
            score -= 5

        return max(0, score)

    def __str__(self) -> str:
        status_emoji = {
            ProjectStatus.ACTIVE: "🟢",
            ProjectStatus.PAUSED: "⏸️",
            ProjectStatus.COMPLETED: "✅",
            ProjectStatus.ARCHIVED: "📦",
            ProjectStatus.BLOCKED: "🚫"
        }
        emoji = status_emoji.get(self.status, "")
        return f"{emoji} {self.name} (P:{self.priority} I:{self.importance} U:{self.urgency})"
