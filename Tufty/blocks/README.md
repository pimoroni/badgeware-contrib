# Blocks & Pill Drop

Two classic puzzle games for the Tufty 2350.

![icon](icon.png)

## Games

**Blocks** — Classic Blocks with SRS rotation, wall kicks, 7-bag randomiser, ghost piece, hold, back-to-back Blocks bonus, and combo tracking.

**Pill Drop** — Clear viruses by matching 4 of the same colour. Pills are two-coloured capsules that you stack and rotate. Chains cascade when floating pill halves drop into new matches. Clear all viruses to advance to the next level.

## Controls

| Button | Action |
|--------|--------|
| A | Move left |
| C | Move right |
| UP | Rotate |
| DOWN | Soft drop |
| B | Hard drop / Start |
| A+B | Pause |
| A+C | Hold piece (Blocks only) |

## Features

- 10 colour themes (random on each launch, changeable from pause menu)
- Persistent high scores and stats
- 3-2-1 countdown before play
- Score popups (SINGLE, DOUBLE, TRIPLE, BLOCKS!, B2B BLOCKS!)
- Danger zone warning when your stack gets high
- Top-out animation on game over
- Pill Drop uses fixed red/blue/yellow colours regardless of theme

## Installing

Copy the `tetris` folder into `/system/apps/` on your Tufty 2350 (double-tap RESET to enter disk mode).

## Files

- `__init__.py` — App entry point, input handling, state machine
- `game.py` — Blocks and Pill Drop game logic
- `draw.py` — All rendering code
- `themes.py` — 10 colour theme definitions
- `stats.py` — Persistent stats tracking
- `icon.png` — 24×24 launcher icon
