# 🎯 Project Decision Tool

Un assistente avanzato per la produttività personale che ti aiuta a:
- **Decidere** su quale progetto/task lavorare
- **Mantenere il focus** con un sistema Pomodoro avanzato
- **Battere la procrastinazione** con tecniche basate sulla ricerca
- **Tracciare i progressi** con gamification (punti, streak, achievements)

## 🚀 Quick Start

### 🌐 Web App (Consigliato)
```bash
# Installa Flask
pip install flask

# Avvia la web app
cd web
python app.py

# Apri http://localhost:5000 nel browser
```

### 💻 CLI (Linea di comando)
```bash
# Avvia l'interfaccia interattiva
python main.py

# Comandi rapidi
python main.py decide    # Raccomandazione su cosa fare
python main.py stats     # Statistiche rapide
python main.py projects  # Lista progetti
python main.py tasks     # Lista task
```

## ✨ Funzionalità

### 🎯 Decision Engine
Il cuore del sistema. Analizza i tuoi progetti e ti dice su cosa dovresti lavorare basandosi su:
- **Importanza e Urgenza** (Matrice Eisenhower)
- **Entusiasmo** (combatte la procrastinazione)
- **Deadline** imminenti
- **Energia richiesta** vs energia disponibile
- **Quick wins** disponibili

Modalità disponibili:
- 🧠 **Smart**: considera tutti i fattori
- ⏰ **Urgente**: prioritizza deadline
- 🔋 **Energy Match**: adatta all'energia attuale
- ⚡ **Quick Wins**: task veloci per momentum
- 🎲 **Random Top 3**: elimina paralisi decisionale

### ⏱️ Focus Mode (Pomodoro Avanzato)
- Timer Pomodoro con display ASCII
- Tracking interruzioni
- Mood tracking (prima/dopo)
- Pause suggerite automaticamente
- Collegamento a task/progetti specifici

### 💡 Anti-Procrastination System
Tecniche basate sulla ricerca di Pychyl, Clear, Newport:
- **Diagnosi del blocco** (task troppo grande? paura? noia?)
- **Micro-tasking automatico** (spacchetta task grandi)
- **2-Minute Rule** e altri interventi
- **Commitment Devices**
- **Implementation Intentions**
- Messaggi motivazionali

### 🏆 Gamification
- **Punti** per ogni azione (task, focus, decisioni)
- **Livelli** (da Novizio a Illuminato)
- **Streak** giornaliere con moltiplicatori
- **20+ Achievements** da sbloccare
- **Sfide giornaliere**

### 📊 Analytics
- Sommario giornaliero/settimanale/mensile
- Productivity Score (0-100)
- Insights personalizzati
- Analisi momento migliore per lavorare
- Trend di focus con grafici ASCII

## 📁 Struttura Progetto

```
project-decision-tool/
├── main.py              # Entry point CLI
├── requirements.txt     # Dipendenze
├── core/                # Logica business
│   ├── database.py      # SQLite database
│   ├── project.py       # Modello Project
│   ├── task.py          # Modello Task
│   ├── decision_engine.py   # Algoritmo decisionale
│   ├── focus_mode.py    # Timer Pomodoro
│   ├── gamification.py  # Punti, livelli
│   ├── anti_procrastination.py
│   └── analytics.py     # Statistiche
├── cli/
│   └── interface.py     # Interfaccia CLI
└── web/                 # 🌐 Web App
    ├── app.py           # Server Flask
    ├── templates/       # HTML
    └── static/          # CSS, JS
```

## 🎮 Come Usare

### 1. Crea i tuoi progetti
Ogni progetto ha:
- Nome e descrizione
- **Importanza** (1-10): quanto impatta sulla tua vita
- **Urgenza** (1-10): quanto è time-sensitive
- **Entusiasmo** (1-10): quanto ti motiva
- Energia richiesta (bassa/media/alta/estrema)
- Ore stimate e deadline (opzionale)

### 2. Aggiungi task ai progetti
I task sono le azioni concrete. Puoi:
- Associarli a progetti
- Stimare i minuti
- Spacchettarli in micro-task

### 3. Chiedi "Cosa dovrei fare adesso?"
Il Decision Engine analizza tutto e ti dice:
- Il progetto/task migliore per questo momento
- Perché è la scelta giusta
- Alternative valide

### 4. Inizia una sessione Focus
- Scegli il tipo (Pomodoro 25min, breve, lunga)
- Collegala al task scelto
- Lavora senza distrazioni
- Guadagna punti e mantieni la streak!

### 5. Quando sei bloccato
Usa il menu Anti-Procrastinazione per:
- Diagnosticare cosa ti blocca
- Ottenere tecniche specifiche
- Spacchettare task grandi
- Creare commitment devices

## 📈 Sistema di Punteggio

| Azione | Punti Base |
|--------|------------|
| Task completato | 10 |
| Micro-task completato | 5 |
| Pomodoro completato | 15 |
| Pomodoro senza interruzioni | 25 |
| Progetto completato | 100 |
| Streak mantenuta | 20 |

**Moltiplicatori Streak:**
- 3 giorni: +10%
- 7 giorni: +25%
- 14 giorni: +50%
- 30 giorni: x2!

## 💾 Dati

I dati vengono salvati in:
```
~/.project_decision_tool/data.db
```

È un database SQLite, puoi:
- Fare backup copiando il file
- Ispezionarlo con qualsiasi client SQLite
- Resettarlo eliminando il file

## 🧠 La Scienza Dietro

Il tool è basato su ricerche di:
- **Timothy Pychyl** (procrastinazione)
- **James Clear** (Atomic Habits)
- **Cal Newport** (Deep Work)
- **Matrice di Eisenhower** (prioritizzazione)
- **Tecnica Pomodoro** (focus)
- **Implementation Intentions** (Gollwitzer)

## 📝 Requisiti

- Python 3.7+
- Nessuna dipendenza esterna (usa solo la libreria standard)
- Terminale con supporto ANSI colors

## 🤝 Contribuire

Il progetto è open source. Sentiti libero di:
- Segnalare bug
- Proporre nuove funzionalità
- Inviare pull request

---

**Ricorda:** L'unico modo per battere la procrastinazione è iniziare. Questo tool ti aiuta a scegliere cosa iniziare. Il resto sta a te! 💪
