# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
python tomato_clock/tomato_clock.py
```

No external dependencies — uses only Python standard library (tkinter, json, os, winsound, threading).

## Architecture

A single-file Tkinter desktop app implementing a Pomodoro timer with:

- **`TomatoClock`** — main class owning the timer state machine (`idle → running/paused`, `work → short_break/long_break`), UI construction, and countdown logic via `root.after()`.
- **`SettingsDialog`** — a modal `Toplevel` for configuring durations and long-break interval; writes to `settings.json` alongside the script.
- **Settings** persisted as JSON in the same directory as the script, loaded on startup with defaults for any missing keys.

State transitions happen in `_tick()` (each second) and `_on_timer_end()` (when the countdown hits zero, which increments the tomato counter, switches mode, and triggers a sound notification via `winsound.Beep`).
