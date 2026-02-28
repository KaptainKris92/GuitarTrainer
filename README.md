# GuitarTrainer

## Installation

### Prerequisites
- Python 3.12
- Windows audio stack support for `pyaudio`/`aubio`

### Install steps
1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`

If wheel/build errors occur (typically for `aubio`/`pyaudio` on Windows):
- Install [Visual Studio Community 2022](https://visualstudio.microsoft.com/vs/community/) with:
  - `Python development`
  - `Python native development tools`
  - `Python web support`
- If still needed, install `Desktop development with C++` from Visual Studio Build Tools.
- Then run:
  - `pip install --upgrade pip wheel setuptools`

## Running the app
Run:
- `python main.py`

## App flow (current UI)

1. In the main menu, select an input device and click `Use Device`.
2. Open either:
   - `Open Tuner`
   - `Open Note Trainer`

### Tuner
- Play one string at a time.
- The UI shows:
  - detected note
  - detected frequency
  - cents offset
  - tune direction hints (`Tune Down` / `Tune Up`)
  - `IN TUNE` indicator when within threshold

### Note Trainer
- Set:
  - `Time per trial (seconds)`
  - `Total trials`
- Click `Start Session`.
- Use `Cancel Session` to stop after the current trial.
- Progress markers update per trial (correct/incorrect).
- `High Scores` shows best runs by game settings.
- `Missed Notes` shows most frequently missed notes in a chart.

## Data storage
- SQLite database: `databases/score_database.db`
- Stores:
  - per-trial results (`score_log`)
  - final game scores (`final_score_log`)

## Screenshots
Current screenshots in `screenshots/` are from earlier UI iterations and should be refreshed to match the latest PySide6 interface.
- Main Menu: `screenshots/01-MainMenu.png`
- Note Trainer: `screenshots/02a-NoteTrainerMain1.png`, `screenshots/02b-NoteTrainerMain2.png`
- High Scores: `screenshots/03-NoteTrainerHighScore.png`
- Missed Notes: `screenshots/04-NoteTrainerMissedNotes.png`
- Console output: `screenshots/05-ConsoleLog.png`

## Attribution

Guitar tuner is based off [this project ](https://github.com/TomSchimansky/GuitarTuner) by [Tom Schimansky](https://github.com/TomSchimansky).
