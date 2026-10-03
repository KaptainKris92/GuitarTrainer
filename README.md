# GuitarTrainer

A web app that gamifies guitar practice: fretboard notes, scales, intervals and music theory.
Built with Svelte and TypeScript in `web/`.

## Running the app

On Windows, double-click `Launch Guitar Trainer.bat`. It installs dependencies on first run,
starts the app and opens it in your browser.

Or manually:

- `cd web`
- `npm install`
- `npm run dev`, then open http://localhost:5173
- `npm test` runs the unit tests

Progress is saved per player in the browser you use, at that address. Use the player menu's
"Export backup" to keep a copy or move it to another browser.

Answer exercises by playing your guitar (the browser will ask for microphone access) or by
tapping the on-screen fretboard.

## What is in it

- **Skill tree** of ten exercises in four tracks. Each one unlocks when the one before it is 25% mastered
  (or tick "Unlock all exercises" in the player menu).
  - Fretboard: find the note, find the interval, build the chord, play the scale
  - Theory: key signatures, chords in a key
  - Ear: hear the interval, play it back
  - Reading: name the note, play the note
- **Daily session**: ten mixed questions weighted towards your weak spots.
- **Difficulty options**: per-question time limit and one-attempt mode. High scores are kept per mode.
- **Players**: progress, XP, level and day streak per player.
- **Scales** explorer and a **tuner**.

The original Python (PySide6) version of the app lives on the `feature/scale-selection` branch.
