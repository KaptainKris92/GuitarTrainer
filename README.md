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

The original Python (PySide6) version of the app lives on the `feature/scale-selection` branch.
