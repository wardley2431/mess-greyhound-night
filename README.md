# Mess Greyhound Night

A browser-based control system for a virtual greyhound race night. One organiser runs the admin console, while TVs around the Mess open the display screen.

The app uses only the Python standard library at runtime and stores event data in `data/race-night-state.json`.

## Features

- Shared login at `/`, routing admins to `/admin` and punters to `/punter`.
- Organiser/admin console at `/admin`.
- TV display at `/display`.
- Punter phone login at `/punter`.
- Ten-race card generated from the fictional dog list, with six dogs per race.
- Player registration with a default 25 Mess Coin starting balance.
- Four-digit PINs generated for each punter.
- Configurable maximum Mess Coin stake per punter per race.
- Whole-coin bet entry against traps 1-6.
- Admin-started one-minute betting countdown with automatic betting close.
- Random race video draw as soon as the countdown expires.
- Winning trap recording from the selected video.
- Tote payout calculation, split proportionally between winning backers.
- Automatic balance updates, race history, leaderboard, and final standings.
- CSV export at `/api/export/ledger.csv`.

## Run Locally

Start the server:

```powershell
.\start.ps1
```

Open the login page:

```text
http://127.0.0.1:8000/
```

Open the TV display:

```text
http://127.0.0.1:8000/display
```

Open the punter phone login:

```text
http://127.0.0.1:8000/punter
```

Optional environment variables:

```text
RACE_HOST=127.0.0.1
RACE_PORT=8000
RACE_ADMIN_NUMBER=0
RACE_ADMIN_PIN=0000
```

## Race Videos

The Video Library is in the admin console. Add each pre-recorded race video with:

- A title.
- A video source, such as `/videos/race01.mp4` or a full HTTPS URL.
- The winning trap number from that video.

For local videos, place files under `static/videos/` and use paths like:

```text
/videos/race01.mp4
```

Betting can stay open while the organiser takes bets. When the organiser presses **Start Countdown**, the one-minute timer begins; at zero the app closes betting and randomly draws a race video. The app avoids reusing videos until the library has been exhausted.

## Punter Login

The default login page is `/`. Admins log in with the configured admin number and PIN, then the app redirects to `/admin`. By default the admin number is `0` and the admin PIN is `0000`; change them with `RACE_ADMIN_NUMBER` and `RACE_ADMIN_PIN`.

Each player has a punter number and a generated PIN. The player table does not keep the PIN visible, but the admin sees it briefly when adding a punter or resetting their PIN. Give those two values to the punter so they can log in from their phone at `/punter`.

The admin can reset a player's PIN from the same table. Phone bets are accepted only while the current race is open, and the server checks the punter number, PIN, available balance, selected trap, stake, and the configured per-race maximum before recording the bet. Bets can be spread across dogs, but their combined stake for that race cannot exceed the maximum.

## Tote Payouts

Stakes are deducted as bets are recorded. When the result is declared, the whole race pool is shared between winning bets in proportion to their stakes.

Because Mess Coins are whole numbers, any remainder is distributed one coin at a time to the winning bets with the largest fractional remainder. If nobody backs the winning trap, the race pool is marked as unclaimed.

## Run In Docker

Build and start:

```bash
docker compose up --build -d
```

Then open:

```text
http://localhost:8010/admin
http://localhost:8010/display
```

The Compose setup is suitable for a Raspberry Pi running Docker. It keeps event state in the named Docker volume `race-night-data`, so players, balances, bets, results, and the current race survive container rebuilds.

For local race videos, create `static/videos/` beside `docker-compose.yml`, copy your `.mp4` files into it, and reference them in the admin Video Library as `/videos/filename.mp4`. The folder is mounted read-only into the container and is ignored by Git so large video files are not pushed to GitHub.

From another device on the same network, replace `localhost` with the Pi address:

```text
http://RASPBERRY_PI_IP:8010/
http://RASPBERRY_PI_IP:8010/display
```

## API

Useful endpoints:

```text
GET  /api/health
GET  /api/state
GET  /api/admin/state
GET  /api/export/ledger.csv
POST /api/login
POST /api/players/add
POST /api/players/reset-pin
POST /api/bets/place
POST /api/punter/login
POST /api/punter/state
POST /api/punter/bet
POST /api/races/close
POST /api/races/draw-video
POST /api/races/record-result
POST /api/races/advance
POST /api/event/finalise
POST /api/event/reset
```
