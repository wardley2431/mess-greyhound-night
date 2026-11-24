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
- Automatic local video discovery, with winning traps saved between events.
- Video streaming with byte ranges for browser playback on the Pi.
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

Place local recordings in `static/videos/`. MP4, M4V, WebM, and OGV files appear automatically in the admin **Video Library**, including files added while the server is running.

Select the real winning trap next to each recording once. The app does not infer winners from the filenames or footage. Those settings survive restarts, container rebuilds, and **Reset Night**. Resetting the night still clears players, bets, and results.

Only entries marked **Ready** enter the random draw. Missing files, incomplete Git LFS downloads, and recordings without a winning trap are excluded. Countdown cannot start until at least one recording is ready. Removing a local entry keeps it excluded from automatic discovery; use **Add Video** with its source to restore it.

Video files stored on GitHub use Git LFS. After pulling the application on the Pi, download the actual recordings:

```bash
git lfs pull
```

The source link beside each recording opens it directly for checking. Local sources look like:

```text
/videos/race01.mp4
```

The **Add Video** form also accepts direct HTTP(S) video URLs, or updates the title and winner of an existing local entry without duplicating it. The browser must support the recording's video codec; changing the filename to `.mp4` does not convert the codec.

The TV player autoplays muted, has playback controls, and displays a retry button if playback fails. A retry keeps the same selected recording. For an older race that drew a blank demo entry, configure the real library and click **Draw Video** to recover that race without clearing bets.

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

For local race videos, create `static/videos/` beside `docker-compose.yml` and copy your files into it, or run `git lfs pull` to download tracked recordings. The folder is mounted read-only into the container. Files are discovered automatically; set each winning trap once in the admin Video Library. Configuration is kept in the persistent `race-night-data` volume.

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
