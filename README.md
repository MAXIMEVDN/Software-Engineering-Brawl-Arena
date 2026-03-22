# Brawl Arena

Brawl Arena is a 2D platform fighter built with Python and Pygame. The project supports local play and networked multiplayer, includes a lobby flow, pre-round stat allocation, round-based upgrades, collectible coins, ultimates, and a final stock-based round.

## Project Overview

The game is structured around a shared authoritative game state:

- `client.py` runs the main Pygame loop, UI flow, rendering, and local/network input handling.
- `server.py` runs the authoritative multiplayer server and advances the match at a fixed tick rate.
- `game_state.py` owns players, rounds, shops, coins, and phase transitions.
- `entities/` contains characters, attacks, platforms, and shared character behavior.
- `systems/` contains collision, animation, physics, and visual effect systems.
- `ui/` contains the main menu, HUD, stat selection screen, upgrade shop, and text rendering helpers.

## Current Gameplay Flow

The current version of the game uses a round-based structure:

1. Players join a lobby.
2. Once at least 2 players are present, the stat selection phase starts automatically.
3. Each player distributes build points across:
   - `power`
   - `defense`
   - `mobility`
   - `knockback`
   - `range`
4. The match starts with timed preliminary rounds.
5. Players earn coins through kills, round rewards, and map coin pickups.
6. Between rounds, players enter an upgrade shop where they can:
   - upgrade stats
   - undo same-round upgrades
   - buy ultimates
   - equip owned ultimates
7. After the preliminary rounds, the game transitions into a final stock-based round.
8. The last player remaining wins.

## Features

- Local play mode
- Multiplayer host/join flow over TCP sockets
- Shared authoritative server game state
- Multiple arena layouts and stage backgrounds
- Round-based progression
- Build allocation before the match
- Between-round upgrade shop
- Coin economy
- Ultimate abilities:
  - Teleportation
  - Fireball
  - Invisibility
  - Grab
  - Parry Counter
- HUD, menu system, character select, and winner screens
- Visual feedback such as hit particles, dash trails, and screen shake

## Current Playable Character

At the moment, the active playable fighter in the codebase is:

- `Warrior`

The warrior is a balanced melee-focused character with:

- Light attack: `Quick Punch`
- Heavy attack: `Power Kick`
- Special attack: `Spinning Slash`

## Tech Stack

- Python
- Pygame
- Standard library networking via `socket`
- `pickle` for state/message serialization
- Optional `Pillow` support for GIF/frame loading

## Requirements

Recommended:

- Python 3.11+
- `pygame`
- `Pillow`

Install dependencies with:

```bash
pip install pygame pillow
```

If you do not install `Pillow`, the game can still run, but some GIF-based asset loading may fall back or be limited.

## Running the Project

Start the client:

```bash
python client.py
```

You can also start the authoritative server manually:

```bash
python server.py
```

If you host through the in-game menu, the client will attempt to launch `server.py` automatically.

## Multiplayer

Brawl Arena supports both:

- `Local Game`
- `Host Game` / `Join Game`

### Host flow

1. Open the game.
2. Choose `Host Game`.
3. Start the lobby.
4. Share the shown IP address with the other player.

### Join flow

1. Open the game.
2. Choose `Join Game`.
3. Enter the host IP.
4. Join the lobby.

The server starts the stat selection phase automatically once at least 2 players are connected.

## Controls

Default controls:

- Move left: `A` or `Left Arrow`
- Move right: `D` or `Right Arrow`
- Aim up: `W` or `Up Arrow`
- Crouch/down: `S` or `Down Arrow`
- Jump: `W`, `Up Arrow`, or `Space`
- Dash: `Left Shift` or `Right Shift`
- Light attack: `J`
- Heavy attack: `K`
- Special attack: `L`
- Ultimate ability: `U`
- Toggle fullscreen: `F11` or `Alt+Enter`
- Return to menu / quit screen: `Esc`

## Match Rules and Important Defaults

Some important gameplay defaults currently configured in `config.py`:

- Resolution: `1280x720`
- FPS: `60`
- Max players: `4`
- Stat selection time: `30 seconds`
- Upgrade shop time: `30 seconds`
- Preliminary rounds: `5`
- Preliminary round duration: `45 seconds`
- Final round stocks: `5`

## Project Structure

```text
Software-Engineering-Brawl-Arena/
├── client.py
├── server.py
├── game_state.py
├── network.py
├── config.py
├── entities/
│   ├── base_character.py
│   ├── base_character_rendering.py
│   ├── base_character_shared.py
│   ├── base_character_state.py
│   ├── base_character_ultimates.py
│   ├── attack.py
│   ├── platform.py
│   ├── coin_pickup.py
│   └── warrior.py
├── systems/
│   ├── animation.py
│   ├── collision.py
│   ├── effects.py
│   └── physics.py
├── ui/
│   ├── menu.py
│   ├── hud.py
│   ├── character_select.py
│   ├── upgrade_shop.py
│   └── title_text.py
└── assets/
```

## Architecture Summary

### Client

The client is responsible for:

- window creation
- rendering
- UI screens
- collecting local input
- syncing state with the server when playing online

### Server

The server is authoritative and responsible for:

- lobby admission
- player input buffering
- fixed-tick simulation
- collision resolution
- game state updates
- broadcasting the latest shared state back to clients on request

### Shared game state

`GameState` is the central source of truth for:

- connected players
- phases such as `lobby`, `stat_select`, `playing`, `round_end`, `upgrade_shop`, and `game_over`
- stage selection and platform layout
- coins and round rewards
- upgrades and ultimates
- transitions into the final round

## Assets

The repository includes:

- backgrounds
- tilesets
- fonts
- sprite sheets
- attack/ultimate visuals
- menu art and icons

These assets are used directly by the Pygame client for menus, stages, effects, and character rendering.

## Notes for Development

- The codebase is currently centered around one active playable character implementation.
- The multiplayer flow uses `pickle`-serialized messages over TCP sockets.
- The game supports both offline and online flows using the same shared `GameState` model.
- Most gameplay tuning lives in `config.py`.

## Possible Future Improvements

- Add more playable characters
- Add AI opponents for local mode
- Improve server discovery / LAN browsing
- Add tests for core game-state transitions
- Add a dependency file such as `requirements.txt`
- Add packaging or a release build process

## Authors

Built as part of the `Software-Engineering-Brawl-Arena` project.
