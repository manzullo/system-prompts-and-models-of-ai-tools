"""
Anti-Procrastination System - Tecniche per combattere la procrastinazione.
Include: spacchettamento task, tecniche motivazionali, accountability.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .database import Database
from .task import Task, TaskSuggestion


class ProcrastinationReason(Enum):
    """Motivi comuni di procrastinazione."""
    TOO_BIG = "too_big"           # Task troppo grande
    UNCLEAR = "unclear"           # Non chiaro cosa fare
    BORING = "boring"             # Noioso
    SCARY = "scary"               # Paura di fallire
    PERFECTIONISM = "perfectionism"  # Perfezionismo
    LOW_ENERGY = "low_energy"     # Poca energia
    OVERWHELMED = "overwhelmed"   # Sopraffatto
    UNKNOWN = "unknown"


@dataclass
class ProcrastinationIntervention:
    """Un intervento per combattere la procrastinazione."""
    reason: ProcrastinationReason
    technique: str
    action: str
    message: str


class AntiProcrastination:
    """
    Sistema anti-procrastinazione con tecniche psicologiche
    basate sulla ricerca (Pychyl, Clear, Newport).
    """

    # Tecniche per ogni tipo di blocco
    INTERVENTIONS = {
        ProcrastinationReason.TOO_BIG: [
            ProcrastinationIntervention(
                reason=ProcrastinationReason.TOO_BIG,
                technique="2-Minute Start",
                action="Lavora solo 2 minuti su questo task",
                message="Non devi finirlo. Solo 2 minuti. Il resto verrà naturalmente."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.TOO_BIG,
                technique="Micro-tasking",
                action="Spacchetta in 5 micro-task",
                message="Un elefante si mangia un boccone alla volta 🐘"
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.TOO_BIG,
                technique="Next Physical Action",
                action="Qual è la PROSSIMA azione fisica?",
                message="Non pensare al task. Pensa al primo movimento delle tue dita."
            ),
        ],
        ProcrastinationReason.UNCLEAR: [
            ProcrastinationIntervention(
                reason=ProcrastinationReason.UNCLEAR,
                technique="Clarification Sprint",
                action="5 minuti per definire esattamente cosa fare",
                message="L'ambiguità è il nemico dell'azione. Definisci il successo."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.UNCLEAR,
                technique="Done Definition",
                action="Scrivi: 'Questo task è FATTO quando...'",
                message="Se non sai dove stai andando, non ci arriverai mai."
            ),
        ],
        ProcrastinationReason.BORING: [
            ProcrastinationIntervention(
                reason=ProcrastinationReason.BORING,
                technique="Temptation Bundling",
                action="Abbina a qualcosa di piacevole",
                message="Musica preferita? Caffè speciale? Rendilo un momento tuo."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.BORING,
                technique="Gamification",
                action="Sfida te stesso con un timer",
                message="Quanto velocemente puoi farlo? Batti il tuo record! ⏱️"
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.BORING,
                technique="Why Chain",
                action="Chiediti 'Perché?' 5 volte",
                message="Trova il significato profondo. Perché questo è importante?"
            ),
        ],
        ProcrastinationReason.SCARY: [
            ProcrastinationIntervention(
                reason=ProcrastinationReason.SCARY,
                technique="Fear Setting",
                action="Scrivi la cosa peggiore che può succedere",
                message="La paura è più grande nella tua testa. Portala alla luce."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.SCARY,
                technique="Worst First Draft",
                action="Fai intenzionalmente una versione TERRIBILE",
                message="Permesso di fare schifo. Il primo draft può essere orrendo."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.SCARY,
                technique="10/10/10",
                action="Come ti sentirai tra 10min/10mesi/10anni se lo fai?",
                message="Di solito la paura svanisce appena iniziamo."
            ),
        ],
        ProcrastinationReason.PERFECTIONISM: [
            ProcrastinationIntervention(
                reason=ProcrastinationReason.PERFECTIONISM,
                technique="80% Rule",
                action="Mira all'80%, non al 100%",
                message="Fatto è meglio di perfetto. L'80% è spesso abbastanza."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.PERFECTIONISM,
                technique="Time Boxing",
                action="Dai un tempo massimo, poi STOP",
                message="La scadenza ti libera dal perfezionismo."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.PERFECTIONISM,
                technique="Version 1.0",
                action="Questa è solo la versione 1.0",
                message="Puoi sempre migliorarla dopo. Ora: spediscila."
            ),
        ],
        ProcrastinationReason.LOW_ENERGY: [
            ProcrastinationIntervention(
                reason=ProcrastinationReason.LOW_ENERGY,
                technique="Energy Match",
                action="Scegli un task adatto alla tua energia",
                message="Non forzarti. Scegli qualcosa di leggero ma produttivo."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.LOW_ENERGY,
                technique="5-Minute Movement",
                action="5 minuti di movimento fisico prima",
                message="Una breve passeggiata o stretching può cambiare tutto."
            ),
        ],
        ProcrastinationReason.OVERWHELMED: [
            ProcrastinationIntervention(
                reason=ProcrastinationReason.OVERWHELMED,
                technique="One Thing",
                action="Scegli UNA sola cosa per oggi",
                message="Ignora tutto il resto. Una cosa. Fatta bene."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.OVERWHELMED,
                technique="Brain Dump",
                action="Scrivi tutto quello che hai in testa (2 min)",
                message="Svuota la mente su carta. Poi scegli una cosa sola."
            ),
            ProcrastinationIntervention(
                reason=ProcrastinationReason.OVERWHELMED,
                technique="Tomorrow List",
                action="Metti il resto nella lista di domani",
                message="Non oggi. Oggi solo questo. Il resto può aspettare."
            ),
        ],
    }

    # Frasi motivazionali
    MOTIVATION_QUOTES = [
        "Il momento migliore era ieri. Il secondo migliore è ORA. 🚀",
        "Non devi vedere tutta la scala. Fai solo il primo gradino. 🪜",
        "Inizia dove sei. Usa quello che hai. Fai quello che puoi. 💪",
        "L'unico modo di fare un ottimo lavoro è amare quello che fai. ❤️",
        "Fatto è meglio che perfetto. 🏁",
        "Ogni maestro era un disastro all'inizio. 🎓",
        "Il tuo io futuro ti ringrazierà. 🙏",
        "Non aspettare la motivazione. Inizia e la motivazione arriverà. ⚡",
        "Piccoli progressi ogni giorno portano a grandi risultati. 📈",
        "Hai battuto il 100% dei giorni che hai iniziato. 🏆"
    ]

    def __init__(self, db: Database):
        self.db = db

    def diagnose_block(self, task: Task = None) -> ProcrastinationReason:
        """
        Cerca di diagnosticare il motivo del blocco.
        Basato su euristiche dal task.
        """
        if not task:
            return ProcrastinationReason.UNKNOWN

        # Task troppo lungo
        if task.estimated_minutes >= 60:
            return ProcrastinationReason.TOO_BIG

        # Task senza descrizione chiara
        if not task.description and len(task.name) < 20:
            return ProcrastinationReason.UNCLEAR

        # Low excitement nel progetto associato
        if task.project_id:
            project = self.db.get_project(task.project_id)
            if project and project.get('excitement', 5) <= 3:
                return ProcrastinationReason.BORING

        return ProcrastinationReason.UNKNOWN

    def get_intervention(self, reason: ProcrastinationReason = None,
                        task: Task = None) -> ProcrastinationIntervention:
        """
        Ottiene un intervento anti-procrastinazione.
        """
        if reason is None:
            reason = self.diagnose_block(task)

        if reason == ProcrastinationReason.UNKNOWN:
            # Intervento generico: 2-minute rule
            return ProcrastinationIntervention(
                reason=reason,
                technique="2-Minute Rule",
                action="Lavora solo 2 minuti. Se vuoi smettere dopo, ok.",
                message="Il segreto è iniziare. Solo 2 minuti."
            )

        interventions = self.INTERVENTIONS.get(reason, [])
        if interventions:
            return random.choice(interventions)

        return ProcrastinationIntervention(
            reason=reason,
            technique="Just Start",
            action="Fai la cosa più piccola possibile",
            message="Inizia. Il resto seguirà."
        )

    def ask_block_questions(self) -> List[Tuple[str, ProcrastinationReason]]:
        """
        Domande per identificare il blocco.
        Ritorna lista di (domanda, reason_se_sì).
        """
        return [
            ("Il task sembra troppo grande o lungo?", ProcrastinationReason.TOO_BIG),
            ("Non sai esattamente cosa devi fare?", ProcrastinationReason.UNCLEAR),
            ("Lo trovi noioso o poco interessante?", ProcrastinationReason.BORING),
            ("Hai paura di sbagliare o di non farlo bene?", ProcrastinationReason.SCARY),
            ("Senti di dover farlo perfettamente?", ProcrastinationReason.PERFECTIONISM),
            ("Ti senti stanco o con poca energia?", ProcrastinationReason.LOW_ENERGY),
            ("Ti senti sopraffatto da troppe cose da fare?", ProcrastinationReason.OVERWHELMED),
        ]

    def generate_micro_tasks(self, task: Task) -> List[Dict]:
        """
        Genera automaticamente micro-task da un task grande.
        Ritorna lista di dizionari pronti per create_task().
        """
        task_type = TaskSuggestion.detect_task_type(task)
        suggestions = TaskSuggestion.suggest_micro_tasks(task, task_type)

        micro_tasks = []
        time_per_micro = max(5, task.estimated_minutes // len(suggestions))

        for i, suggestion in enumerate(suggestions):
            micro_tasks.append({
                'name': suggestion,
                'project_id': task.project_id,
                'estimated_minutes': time_per_micro,
                'energy_required': task.energy_required.value,
                'is_micro_task': True,
                'parent_task_id': task.id,
                'order_index': i,
                'priority': task.priority
            })

        return micro_tasks

    def create_micro_tasks_in_db(self, task: Task) -> List[int]:
        """
        Crea i micro-task nel database e ritorna i loro ID.
        """
        micro_tasks = self.generate_micro_tasks(task)
        task_ids = []

        for mt in micro_tasks:
            task_id = self.db.create_task(**mt)
            task_ids.append(task_id)

        return task_ids

    def get_motivation_message(self) -> str:
        """Ritorna un messaggio motivazionale casuale."""
        return random.choice(self.MOTIVATION_QUOTES)

    def get_startup_ritual(self) -> List[str]:
        """
        Ritorna un rituale di startup per iniziare a lavorare.
        Aiuta a superare l'inerzia iniziale.
        """
        return [
            "☕ 1. Prepara la tua bevanda preferita (2 min)",
            "🧹 2. Pulisci la scrivania - solo l'essenziale (1 min)",
            "📱 3. Telefono in modalità aereo o in un'altra stanza",
            "🎯 4. Scrivi l'UNICA cosa che farai in questa sessione",
            "⏱️ 5. Imposta un timer e INIZIA",
            "",
            "💡 Ricorda: non devi finire. Devi solo INIZIARE."
        ]

    def get_commitment_device(self, task: Task) -> Dict:
        """
        Crea un 'commitment device' - un impegno formale.
        """
        now = datetime.now()
        deadline = now + timedelta(minutes=task.estimated_minutes + 10)

        return {
            "commitment": f"Mi impegno a lavorare su '{task.name}' per {task.estimated_minutes} minuti",
            "start_time": now.strftime("%H:%M"),
            "end_time": deadline.strftime("%H:%M"),
            "reward": "Una pausa meritata e punti guadagnati!",
            "consequence": "Annotare perché non ho iniziato (per capire il pattern)",
        }

    def get_resistance_score(self, task: Task) -> Tuple[int, str]:
        """
        Calcola quanto 'resistenza' il task genera.
        1-10, dove 10 = massima resistenza/procrastinazione.
        """
        score = 0
        reasons = []

        # Durata
        if task.estimated_minutes >= 60:
            score += 3
            reasons.append("Durata lunga")
        elif task.estimated_minutes >= 30:
            score += 1

        # Energia richiesta
        from .project import EnergyLevel
        if task.energy_required == EnergyLevel.EXTREME:
            score += 2
            reasons.append("Alta energia richiesta")
        elif task.energy_required == EnergyLevel.HIGH:
            score += 1

        # Vaghezza del nome
        if len(task.name) < 15 and not task.description:
            score += 2
            reasons.append("Task vago")

        # Non è un micro-task
        if not task.is_micro_task:
            score += 1

        # In ritardo
        if task.is_overdue:
            score += 2
            reasons.append("In ritardo (ansia)")

        # Normalizza 1-10
        score = min(10, max(1, score))

        reason_text = ", ".join(reasons) if reasons else "Sembra gestibile!"

        return score, reason_text

    def suggest_procrastination_tax(self, task: Task) -> str:
        """
        Suggerisce una 'tassa' per procrastinare - rende il
        non-fare più costoso del fare.
        """
        suggestions = [
            f"Se non inizi entro 5 minuti: 10 jumping jacks prima di poter procrastinare 🏃",
            f"Regola: prima di scrollare il telefono, devi lavorare 2 minuti su questo 📱",
            f"Ogni 30 minuti di rimando = 5€ nel 'barattolo della procrastinazione' 💰",
            f"Se non lo fai oggi, domani dovrai farlo + un task extra ➕",
            f"Dillo a qualcuno: 'Finisco questo entro le [ora]' - accountability! 🗣️"
        ]

        return random.choice(suggestions)

    def get_implementation_intention(self, task: Task) -> str:
        """
        Crea un 'implementation intention' (Gollwitzer).
        Formula: "Quando X, farò Y in Z"
        """
        now = datetime.now()
        hour = now.hour

        if hour < 12:
            when = "dopo il mio caffè mattutino"
        elif hour < 14:
            when = "subito dopo pranzo"
        elif hour < 18:
            when = "prima della prossima riunione"
        else:
            when = "prima di cena"

        return f"Quando {when}, lavorerò su '{task.name}' alla mia scrivania per almeno {min(15, task.remaining_minutes)} minuti."
