from __future__ import annotations

import calendar
import copy
import csv
import io
import json
import mimetypes
import os
import random
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DATA_DIR = ROOT / "data"
STATE_FILE = DATA_DIR / "race-night-state.json"
STATE_LOCK = threading.RLock()

DEFAULT_STARTING_BALANCE = 25
DEFAULT_RACE_COUNT = 10
DEFAULT_MAX_RACE_STAKE = 10
DEFAULT_BETTING_COUNTDOWN_SECONDS = 60
ADMIN_REFERENCE = str(os.environ.get("RACE_ADMIN_NUMBER", "0")).strip() or "0"
ADMIN_PIN = str(os.environ.get("RACE_ADMIN_PIN", "0000")).strip() or "0000"

DOGS: list[dict[str, Any]] = [
    {"dogId": 1, "name": "CO's Driver", "age": 5},
    {"dogId": 2, "name": "Green Slime", "age": 3},
    {"dogId": 3, "name": "Certa Cito", "age": 6},
    {"dogId": 4, "name": "Hurry Up & Wait", "age": 4},
    {"dogId": 5, "name": "Five Miles of Death", "age": 7},
    {"dogId": 6, "name": "Fill Your Boots", "age": 2},
    {"dogId": 7, "name": "Duty Trainer", "age": 5},
    {"dogId": 8, "name": "Butts Party", "age": 8},
    {"dogId": 9, "name": "Mess Bill", "age": 3},
    {"dogId": 10, "name": "Guard Commander", "age": 6},
    {"dogId": 11, "name": "Snorker", "age": 4},
    {"dogId": 12, "name": "Robocop", "age": 5},
    {"dogId": 13, "name": "ENDEX", "age": 7},
    {"dogId": 14, "name": "Top Student", "age": 2},
    {"dogId": 15, "name": "Pays to be a Winner", "age": 5},
    {"dogId": 16, "name": "Scaleyback", "age": 3},
    {"dogId": 17, "name": "Radio Check", "age": 6},
    {"dogId": 18, "name": "CUMDAFER", "age": 4},
    {"dogId": 19, "name": "Going Ashore", "age": 5},
    {"dogId": 20, "name": "Egyptian PT", "age": 6},
    {"dogId": 21, "name": "Chairborne", "age": 4},
    {"dogId": 22, "name": "On Stag", "age": 3},
    {"dogId": 23, "name": "HMS Pickle", "age": 5},
    {"dogId": 24, "name": "Have You Read Orders?", "age": 2},
    {"dogId": 25, "name": "Picking Up The Brass", "age": 6},
    {"dogId": 26, "name": "Room Inspection", "age": 4},
    {"dogId": 27, "name": "Port Stain", "age": 3},
    {"dogId": 28, "name": "Knock Off", "age": 6},
    {"dogId": 29, "name": "Muster Parade", "age": 4},
    {"dogId": 30, "name": "Eyebrows Gen", "age": 3},
]

DEFAULT_VIDEO_LIBRARY: list[dict[str, Any]] = [
    {"id": "video-01", "title": "Race Video 01", "source": "", "winningTrap": 1},
    {"id": "video-02", "title": "Race Video 02", "source": "", "winningTrap": 4},
    {"id": "video-03", "title": "Race Video 03", "source": "", "winningTrap": 2},
    {"id": "video-04", "title": "Race Video 04", "source": "", "winningTrap": 6},
    {"id": "video-05", "title": "Race Video 05", "source": "", "winningTrap": 3},
    {"id": "video-06", "title": "Race Video 06", "source": "", "winningTrap": 5},
    {"id": "video-07", "title": "Race Video 07", "source": "", "winningTrap": 2},
    {"id": "video-08", "title": "Race Video 08", "source": "", "winningTrap": 1},
    {"id": "video-09", "title": "Race Video 09", "source": "", "winningTrap": 5},
    {"id": "video-10", "title": "Race Video 10", "source": "", "winningTrap": 6},
    {"id": "video-11", "title": "Race Video 11", "source": "", "winningTrap": 3},
    {"id": "video-12", "title": "Race Video 12", "source": "", "winningTrap": 4},
]


class ApiError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(message)
        self.status = status


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def iso_from_timestamp(timestamp: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))


def parse_iso_timestamp(value: Any) -> float | None:
    if not value:
        return None
    try:
        return float(calendar.timegm(time.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ")))
    except (TypeError, ValueError):
        return None


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def random_pin() -> str:
    return f"{random.SystemRandom().randrange(0, 10_000):04d}"


def bounded_int(value: Any, field_name: str, *, minimum: int, maximum: int) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(f"{field_name} must be a whole number") from exc
    if numeric < minimum or numeric > maximum:
        raise ApiError(f"{field_name} must be between {minimum} and {maximum}")
    return numeric


def clean_text(value: Any, field_name: str, *, maximum: int = 120) -> str:
    text = str(value or "").strip()
    if not text:
        raise ApiError(f"{field_name} is required")
    if len(text) > maximum:
        raise ApiError(f"{field_name} must be {maximum} characters or fewer")
    return text


def build_lineups(race_count: int = DEFAULT_RACE_COUNT, seed: int | None = None) -> list[list[dict[str, Any]]]:
    generator = random.Random(seed if seed is not None else time.time_ns())
    needed = race_count * 6
    copies = max(1, (needed + len(DOGS) - 1) // len(DOGS))

    for _ in range(500):
        race_pool = [copy.deepcopy(dog) for _ in range(copies) for dog in DOGS]
        generator.shuffle(race_pool)
        lineups: list[list[dict[str, Any]]] = []
        valid = True
        for race_index in range(race_count):
            selected = race_pool[race_index * 6 : race_index * 6 + 6]
            dog_ids = [dog["dogId"] for dog in selected]
            if len(selected) < 6 or len(dog_ids) != len(set(dog_ids)):
                valid = False
                break
            lineups.append(
                [
                    {
                        "trap": trap,
                        "dogId": dog["dogId"],
                        "name": dog["name"],
                        "age": dog["age"],
                    }
                    for trap, dog in enumerate(selected, start=1)
                ]
            )
        if valid:
            return lineups

    raise RuntimeError("Could not build valid race lineups")


def new_event_state(
    *,
    event_name: str = "Mess Greyhound Night",
    starting_balance: int = DEFAULT_STARTING_BALANCE,
    max_race_stake: int = DEFAULT_MAX_RACE_STAKE,
    betting_countdown_seconds: int = DEFAULT_BETTING_COUNTDOWN_SECONDS,
    race_count: int = DEFAULT_RACE_COUNT,
    seed: int | None = None,
) -> dict[str, Any]:
    starting_balance = max(1, int(starting_balance))
    max_race_stake = max(1, int(max_race_stake))
    betting_countdown_seconds = max(1, int(betting_countdown_seconds))
    race_count = max(1, min(30, int(race_count)))
    created = now_iso()
    races = []
    for index, lineup in enumerate(build_lineups(race_count, seed), start=1):
        races.append(
            {
                "raceNumber": index,
                "status": "open" if index == 1 else "pending",
                "lineup": lineup,
                "bets": [],
                "selectedVideo": None,
                "winningTrap": None,
                "winningDog": None,
                "payouts": [],
                "unclaimedPool": 0,
                "openedAt": created if index == 1 else None,
                "bettingClosesAt": None,
                "closedAt": None,
                "videoDrawnAt": None,
                "resultedAt": None,
            }
        )
    return {
        "schemaVersion": 1,
        "event": {
            "name": event_name,
            "startingBalance": starting_balance,
            "maxRaceStake": max_race_stake,
            "bettingCountdownSeconds": betting_countdown_seconds,
            "status": "running",
            "currentRaceNumber": 1,
            "createdAt": created,
            "updatedAt": created,
        },
        "players": [],
        "races": races,
        "videoLibrary": copy.deepcopy(DEFAULT_VIDEO_LIBRARY),
        "adjustments": [],
    }


def migrate_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("schemaVersion", 1)
    state.setdefault("players", [])
    state.setdefault("races", [])
    state.setdefault("videoLibrary", copy.deepcopy(DEFAULT_VIDEO_LIBRARY))
    state.setdefault("adjustments", [])
    state.setdefault(
        "event",
        {
            "name": "Mess Greyhound Night",
            "startingBalance": DEFAULT_STARTING_BALANCE,
            "maxRaceStake": DEFAULT_MAX_RACE_STAKE,
            "bettingCountdownSeconds": DEFAULT_BETTING_COUNTDOWN_SECONDS,
            "status": "running",
            "currentRaceNumber": 1,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
        },
    )
    state["event"].setdefault("maxRaceStake", DEFAULT_MAX_RACE_STAKE)
    state["event"].setdefault("bettingCountdownSeconds", DEFAULT_BETTING_COUNTDOWN_SECONDS)
    for player in state["players"]:
        player.setdefault("id", make_id("player"))
        player.setdefault("reference", 0)
        player.setdefault("pin", random_pin())
        player.setdefault("startingBalance", DEFAULT_STARTING_BALANCE)
        player.setdefault("balance", player["startingBalance"])
        player.setdefault("active", True)
        player.setdefault("createdAt", now_iso())
    for race in state["races"]:
        race.setdefault("bets", [])
        race.setdefault("selectedVideo", None)
        race.setdefault("winningTrap", None)
        race.setdefault("winningDog", None)
        race.setdefault("payouts", [])
        race.setdefault("unclaimedPool", 0)
        race.setdefault("openedAt", None)
        race.setdefault("bettingClosesAt", None)
        race.setdefault("closedAt", None)
        race.setdefault("videoDrawnAt", None)
        race.setdefault("resultedAt", None)
    return state


def load_state_unlocked() -> dict[str, Any]:
    if not STATE_FILE.exists():
        state = new_event_state()
        save_state_unlocked(state)
        return state
    with STATE_FILE.open("r", encoding="utf-8") as handle:
        return migrate_state(json.load(handle))


def save_state_unlocked(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state["event"]["updatedAt"] = now_iso()
    temp_path = STATE_FILE.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
        handle.write("\n")
    temp_path.replace(STATE_FILE)


def find_race(state: dict[str, Any], race_number: Any | None = None) -> dict[str, Any]:
    number = state["event"].get("currentRaceNumber") if race_number in {None, ""} else race_number
    try:
        numeric = int(number)
    except (TypeError, ValueError) as exc:
        raise ApiError("Race number must be a whole number") from exc
    for race in state["races"]:
        if race["raceNumber"] == numeric:
            return race
    raise ApiError("Race not found", HTTPStatus.NOT_FOUND)


def find_player(state: dict[str, Any], player_id: Any) -> dict[str, Any]:
    for player in state["players"]:
        if player["id"] == player_id:
            return player
    raise ApiError("Player not found", HTTPStatus.NOT_FOUND)


def find_player_by_reference(state: dict[str, Any], reference: Any) -> dict[str, Any]:
    numeric = bounded_int(reference, "Punter number", minimum=1, maximum=999_999)
    for player in state["players"]:
        if int(player.get("reference", 0)) == numeric:
            return player
    raise ApiError("Punter number or PIN is incorrect", HTTPStatus.UNAUTHORIZED)


def authenticate_punter(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    player = find_player_by_reference(state, payload.get("reference"))
    pin = str(payload.get("pin") or "").strip()
    if not pin or pin != str(player.get("pin", "")):
        raise ApiError("Punter number or PIN is incorrect", HTTPStatus.UNAUTHORIZED)
    if not player.get("active", True):
        raise ApiError("This punter is inactive", HTTPStatus.FORBIDDEN)
    return player


def is_admin_login(payload: dict[str, Any]) -> bool:
    reference = str(payload.get("reference") or "").strip().lower()
    pin = str(payload.get("pin") or "").strip()
    admin_references = {ADMIN_REFERENCE.lower(), "admin"}
    return reference in admin_references and pin == ADMIN_PIN


def authenticate_login(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    reference = str(payload.get("reference") or "").strip().lower()
    if is_admin_login(payload):
        return {"role": "admin"}
    if reference in {ADMIN_REFERENCE.lower(), "admin"}:
        raise ApiError("Punter number or PIN is incorrect", HTTPStatus.UNAUTHORIZED)
    player = authenticate_punter(state, payload)
    return {"role": "punter", "punter": punter_summary(state, player)}


def dog_for_trap(race: dict[str, Any], trap: int) -> dict[str, Any]:
    for entry in race["lineup"]:
        if entry["trap"] == trap:
            return entry
    raise ApiError("Trap not found for this race")


def race_pool(race: dict[str, Any]) -> int:
    return sum(int(bet["stake"]) for bet in race["bets"])


def race_totals_by_trap(race: dict[str, Any]) -> list[dict[str, int]]:
    totals = [{"trap": trap, "stake": 0, "bets": 0} for trap in range(1, 7)]
    by_trap = {item["trap"]: item for item in totals}
    for bet in race["bets"]:
        trap_total = by_trap[int(bet["trap"])]
        trap_total["stake"] += int(bet["stake"])
        trap_total["bets"] += 1
    return totals


def race_stake_for_player(race: dict[str, Any], player_id: str) -> int:
    return sum(int(bet["stake"]) for bet in race["bets"] if bet["playerId"] == player_id)


def betting_countdown_seconds(state: dict[str, Any]) -> int:
    return int(state["event"].get("bettingCountdownSeconds", DEFAULT_BETTING_COUNTDOWN_SECONDS))


def set_betting_deadline(state: dict[str, Any], race: dict[str, Any], now_ts: float | None = None) -> None:
    race["bettingClosesAt"] = iso_from_timestamp(
        (time.time() if now_ts is None else now_ts) + betting_countdown_seconds(state)
    )


def select_race_video(state: dict[str, Any], race: dict[str, Any]) -> None:
    if race.get("selectedVideo"):
        raise ApiError("A video has already been selected for this race")
    if not state["videoLibrary"]:
        raise ApiError("No race videos are in the library")

    used_ids = {
        selected["id"]
        for item in state["races"]
        if (selected := item.get("selectedVideo"))
    }
    available = [video for video in state["videoLibrary"] if video["id"] not in used_ids]
    if not available:
        available = state["videoLibrary"]
    race["selectedVideo"] = copy.deepcopy(random.choice(available))
    race["status"] = "video"
    race["videoDrawnAt"] = now_iso()
    race["bettingClosesAt"] = None


def apply_race_timers(state: dict[str, Any], now_ts: float | None = None) -> bool:
    now_value = time.time() if now_ts is None else now_ts
    changed = False
    for race in state["races"]:
        if race.get("status") != "open":
            continue
        if not race.get("bettingClosesAt"):
            continue
        deadline = parse_iso_timestamp(race.get("bettingClosesAt"))
        if deadline is None:
            race["bettingClosesAt"] = None
            changed = True
            continue
        if deadline > now_value:
            continue

        race["status"] = "closed"
        race["closedAt"] = iso_from_timestamp(now_value)
        race["bettingClosesAt"] = None
        changed = True
        try:
            select_race_video(state, race)
        except ApiError as exc:
            race["autoDrawError"] = str(exc)
        else:
            race.pop("autoDrawError", None)
    return changed


def player_totals(state: dict[str, Any]) -> dict[str, dict[str, int]]:
    totals = {
        player["id"]: {"staked": 0, "won": 0, "bets": 0, "adjusted": 0}
        for player in state["players"]
    }
    for race in state["races"]:
        for bet in race["bets"]:
            player_id = bet["playerId"]
            if player_id in totals:
                totals[player_id]["staked"] += int(bet["stake"])
                totals[player_id]["bets"] += 1
        for payout in race.get("payouts", []):
            player_id = payout["playerId"]
            if player_id in totals:
                totals[player_id]["won"] += int(payout["amount"])
    for adjustment in state.get("adjustments", []):
        player_id = adjustment["playerId"]
        if player_id in totals:
            totals[player_id]["adjusted"] += int(adjustment["amount"])
    return totals


def summarized_state(state: dict[str, Any], *, include_private: bool = False) -> dict[str, Any]:
    view = copy.deepcopy(state)
    current = find_race(view)
    totals = player_totals(view)

    for race in view["races"]:
        race["pool"] = race_pool(race)
        race["totalsByTrap"] = race_totals_by_trap(race)
        if race.get("winningTrap") and not race.get("winningDog"):
            race["winningDog"] = dog_for_trap(race, int(race["winningTrap"]))["name"]

    players = []
    for player in view["players"]:
        total = totals[player["id"]]
        enriched = copy.deepcopy(player)
        enriched.update(
            {
                "totalStaked": total["staked"],
                "totalWon": total["won"],
                "totalBets": total["bets"],
                "manualAdjustments": total["adjusted"],
                "profit": int(player["balance"]) - int(player["startingBalance"]),
            }
        )
        if not include_private:
            enriched.pop("pin", None)
        players.append(enriched)
    view["players"] = players
    view["leaderboard"] = sorted(
        players,
        key=lambda item: (int(item["balance"]), int(item["totalWon"]), -int(item["reference"])),
        reverse=True,
    )
    view["currentRace"] = current
    view["totalCoinPool"] = sum(race_pool(race) for race in view["races"])
    if not include_private:
        view["videoLibrary"] = []
        for race in view["races"]:
            if race.get("selectedVideo") and not race.get("winningTrap"):
                race["selectedVideo"].pop("winningTrap", None)
    return view


def punter_summary(state: dict[str, Any], player: dict[str, Any]) -> dict[str, Any]:
    public = summarized_state(state)
    public_player = next(
        item for item in public["players"] if item["id"] == player["id"]
    )
    my_bets = []
    race_summaries = []
    for race in state["races"]:
        bets = [bet for bet in race["bets"] if bet["playerId"] == player["id"]]
        payout_total = sum(
            int(payout["amount"])
            for payout in race.get("payouts", [])
            if payout["playerId"] == player["id"]
        )
        if bets or payout_total:
            race_summaries.append(
                {
                    "raceNumber": race["raceNumber"],
                    "status": race["status"],
                    "staked": sum(int(bet["stake"]) for bet in bets),
                    "payout": payout_total,
                    "winningTrap": race.get("winningTrap"),
                    "winningDog": race.get("winningDog"),
                }
            )
        for bet in bets:
            my_bets.append(
                {
                    "id": bet["id"],
                    "raceNumber": race["raceNumber"],
                    "status": race["status"],
                    "trap": bet["trap"],
                    "dogName": bet["dogName"],
                    "stake": bet["stake"],
                    "placedAt": bet["placedAt"],
                    "winningTrap": race.get("winningTrap"),
                    "winningDog": race.get("winningDog"),
                }
            )
    return {
        "event": public["event"],
        "currentRace": public["currentRace"],
        "player": public_player,
        "leaderboard": public["leaderboard"][:10],
        "myCurrentBets": [
            bet
            for bet in my_bets
            if bet["raceNumber"] == public["currentRace"]["raceNumber"]
        ],
        "myBets": my_bets,
        "myRaceSummaries": race_summaries,
    }


def mutate_state(
    mutator: Callable[[dict[str, Any]], dict[str, Any] | None],
    *,
    include_private: bool = False,
) -> dict[str, Any]:
    with STATE_LOCK:
        state = load_state_unlocked()
        timer_changed = apply_race_timers(state)
        try:
            replacement = mutator(state)
        except Exception:
            if timer_changed:
                save_state_unlocked(state)
            raise
        if replacement is not None:
            state = replacement
        save_state_unlocked(state)
        return summarized_state(state, include_private=include_private)


def add_player(state: dict[str, Any], payload: dict[str, Any]) -> None:
    name = clean_text(payload.get("name"), "Player name", maximum=80)
    starting_balance = bounded_int(
        payload.get("startingBalance", state["event"]["startingBalance"]),
        "Starting balance",
        minimum=0,
        maximum=10_000,
    )
    reference = max((int(player.get("reference", 0)) for player in state["players"]), default=0) + 1
    state["players"].append(
        {
            "id": make_id("player"),
            "reference": reference,
            "pin": random_pin(),
            "name": name,
            "startingBalance": starting_balance,
            "balance": starting_balance,
            "active": True,
            "createdAt": now_iso(),
        }
    )


def reset_player_pin(state: dict[str, Any], payload: dict[str, Any]) -> None:
    player = find_player(state, payload.get("playerId"))
    player["pin"] = random_pin()


def adjust_player(state: dict[str, Any], payload: dict[str, Any]) -> None:
    player = find_player(state, payload.get("playerId"))
    amount = bounded_int(payload.get("amount"), "Adjustment", minimum=-10_000, maximum=10_000)
    new_balance = int(player["balance"]) + amount
    if new_balance < 0:
        raise ApiError("Adjustment would take the player below zero")
    player["balance"] = new_balance
    state["adjustments"].append(
        {
            "id": make_id("adjustment"),
            "playerId": player["id"],
            "playerName": player["name"],
            "amount": amount,
            "reason": str(payload.get("reason") or "Manual adjustment")[:120],
            "createdAt": now_iso(),
        }
    )


def remove_player(state: dict[str, Any], payload: dict[str, Any]) -> None:
    player = find_player(state, payload.get("playerId"))
    has_bets = any(bet["playerId"] == player["id"] for race in state["races"] for bet in race["bets"])
    if has_bets:
        player["active"] = False
    else:
        state["players"] = [item for item in state["players"] if item["id"] != player["id"]]


def update_event(state: dict[str, Any], payload: dict[str, Any]) -> None:
    if "name" in payload:
        state["event"]["name"] = clean_text(payload.get("name"), "Event name", maximum=100)
    if "startingBalance" in payload:
        state["event"]["startingBalance"] = bounded_int(
            payload.get("startingBalance"),
            "Starting balance",
            minimum=1,
            maximum=10_000,
        )
    if "maxRaceStake" in payload:
        state["event"]["maxRaceStake"] = bounded_int(
            payload.get("maxRaceStake"),
            "Maximum race stake",
            minimum=1,
            maximum=10_000,
        )


def open_betting(state: dict[str, Any], payload: dict[str, Any]) -> None:
    race = find_race(state, payload.get("raceNumber"))
    open_race = next((item for item in state["races"] if item["status"] == "open"), None)
    if open_race and open_race["raceNumber"] != race["raceNumber"]:
        raise ApiError(f"Race {open_race['raceNumber']} is already open")
    if race.get("selectedVideo") or race.get("winningTrap"):
        raise ApiError("This race already has a selected video or result")
    if race["status"] not in {"pending", "closed"}:
        raise ApiError("Only pending or closed races can be opened")
    race["status"] = "open"
    race["openedAt"] = race["openedAt"] or now_iso()
    race["bettingClosesAt"] = None
    race["closedAt"] = None
    state["event"]["currentRaceNumber"] = race["raceNumber"]
    state["event"]["status"] = "running"


def start_countdown(state: dict[str, Any], payload: dict[str, Any]) -> None:
    race = find_race(state, payload.get("raceNumber"))
    if race["status"] != "open":
        raise ApiError("Betting must be open before starting the countdown")
    if race.get("selectedVideo") or race.get("winningTrap"):
        raise ApiError("This race already has a selected video or result")
    if race.get("bettingClosesAt"):
        raise ApiError("The countdown is already running for this race")
    set_betting_deadline(state, race)


def close_betting(state: dict[str, Any], payload: dict[str, Any]) -> None:
    race = find_race(state, payload.get("raceNumber"))
    if race["status"] != "open":
        raise ApiError("Betting is not open for this race")
    race["status"] = "closed"
    race["bettingClosesAt"] = None
    race["closedAt"] = now_iso()


def add_video(state: dict[str, Any], payload: dict[str, Any]) -> None:
    title = clean_text(payload.get("title"), "Video title", maximum=100)
    source = str(payload.get("source") or "").strip()[:500]
    winning_trap = bounded_int(payload.get("winningTrap"), "Winning trap", minimum=1, maximum=6)
    state["videoLibrary"].append(
        {
            "id": make_id("video"),
            "title": title,
            "source": source,
            "winningTrap": winning_trap,
        }
    )


def remove_video(state: dict[str, Any], payload: dict[str, Any]) -> None:
    video_id = str(payload.get("videoId") or "")
    used = any((race.get("selectedVideo") or {}).get("id") == video_id for race in state["races"])
    if used:
        raise ApiError("This video has already been selected for a race")
    state["videoLibrary"] = [video for video in state["videoLibrary"] if video["id"] != video_id]


def draw_video(state: dict[str, Any], payload: dict[str, Any]) -> None:
    race = find_race(state, payload.get("raceNumber"))
    if race["status"] != "closed":
        raise ApiError("Close betting before drawing a video")
    select_race_video(state, race)


def place_bet(state: dict[str, Any], payload: dict[str, Any]) -> None:
    race = find_race(state, payload.get("raceNumber"))
    if race["status"] != "open":
        raise ApiError("Betting is closed for this race")

    player = find_player(state, payload.get("playerId"))
    if not player.get("active", True):
        raise ApiError("This player is inactive")

    trap = bounded_int(payload.get("trap"), "Trap", minimum=1, maximum=6)
    dog = dog_for_trap(race, trap)
    stake = bounded_int(payload.get("stake"), "Stake", minimum=1, maximum=10_000)
    max_race_stake = int(state["event"].get("maxRaceStake", DEFAULT_MAX_RACE_STAKE))
    already_staked = race_stake_for_player(race, player["id"])
    if already_staked + stake > max_race_stake:
        remaining = max(0, max_race_stake - already_staked)
        raise ApiError(
            f"Race limit is {max_race_stake} Mess Coins. "
            f"{player['name']} has {remaining} Mess Coins remaining for this race."
        )
    if int(player["balance"]) < stake:
        raise ApiError(f"{player['name']} only has {player['balance']} Mess Coins")

    player["balance"] = int(player["balance"]) - stake
    race["bets"].append(
        {
            "id": make_id("bet"),
            "playerId": player["id"],
            "playerReference": player["reference"],
            "playerName": player["name"],
            "trap": trap,
            "dogId": dog["dogId"],
            "dogName": dog["name"],
            "stake": stake,
            "placedAt": now_iso(),
        }
    )


def place_punter_bet(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    player = authenticate_punter(state, payload)
    place_bet(
        state,
        {
            "raceNumber": payload.get("raceNumber"),
            "playerId": player["id"],
            "trap": payload.get("trap"),
            "stake": payload.get("stake"),
        },
    )
    return player


def void_bet(state: dict[str, Any], payload: dict[str, Any]) -> None:
    race = find_race(state, payload.get("raceNumber"))
    if race.get("winningTrap"):
        raise ApiError("Bets cannot be voided after the result is declared")
    bet_id = str(payload.get("betId") or "")
    for index, bet in enumerate(race["bets"]):
        if bet["id"] == bet_id:
            player = find_player(state, bet["playerId"])
            player["balance"] = int(player["balance"]) + int(bet["stake"])
            race["bets"].pop(index)
            return
    raise ApiError("Bet not found", HTTPStatus.NOT_FOUND)


def calculate_tote_payouts(race: dict[str, Any], winning_trap: int) -> tuple[list[dict[str, Any]], int]:
    pool = race_pool(race)
    winning_bets = [bet for bet in race["bets"] if int(bet["trap"]) == winning_trap]
    winning_stake = sum(int(bet["stake"]) for bet in winning_bets)
    if not winning_bets or winning_stake == 0:
        return [], pool

    payouts = []
    allocated = 0
    for order, bet in enumerate(winning_bets):
        scaled = int(bet["stake"]) * pool
        amount, remainder = divmod(scaled, winning_stake)
        allocated += amount
        payouts.append(
            {
                "betId": bet["id"],
                "playerId": bet["playerId"],
                "playerName": bet["playerName"],
                "playerReference": bet["playerReference"],
                "stake": bet["stake"],
                "amount": amount,
                "_remainder": remainder,
                "_order": order,
            }
        )

    leftovers = pool - allocated
    for payout in sorted(payouts, key=lambda item: (-item["_remainder"], item["_order"]))[:leftovers]:
        payout["amount"] += 1

    grouped: dict[str, dict[str, Any]] = {}
    for payout in payouts:
        player_id = payout["playerId"]
        if player_id not in grouped:
            grouped[player_id] = {
                "id": make_id("payout"),
                "playerId": player_id,
                "playerName": payout["playerName"],
                "playerReference": payout["playerReference"],
                "amount": 0,
                "winningStake": 0,
                "betIds": [],
            }
        grouped[player_id]["amount"] += int(payout["amount"])
        grouped[player_id]["winningStake"] += int(payout["stake"])
        grouped[player_id]["betIds"].append(payout["betId"])
    return list(grouped.values()), 0


def record_result(state: dict[str, Any], payload: dict[str, Any]) -> None:
    race = find_race(state, payload.get("raceNumber"))
    if race["status"] == "open":
        raise ApiError("Close betting before recording the result")
    if race["status"] != "video" or not race.get("selectedVideo"):
        raise ApiError("Draw a race video before recording the result")
    if race.get("winningTrap"):
        raise ApiError("This race already has a result")

    winning_trap = int(race["selectedVideo"]["winningTrap"])
    if payload.get("winningTrap") not in {None, ""}:
        confirmed_trap = bounded_int(payload.get("winningTrap"), "Winning trap", minimum=1, maximum=6)
        if confirmed_trap != winning_trap:
            raise ApiError("Winning trap must match the selected video")

    dog = dog_for_trap(race, winning_trap)
    payouts, unclaimed_pool = calculate_tote_payouts(race, winning_trap)
    for payout in payouts:
        player = find_player(state, payout["playerId"])
        player["balance"] = int(player["balance"]) + int(payout["amount"])

    race["winningTrap"] = winning_trap
    race["winningDog"] = dog["name"]
    race["payouts"] = payouts
    race["unclaimedPool"] = unclaimed_pool
    race["status"] = "resulted"
    race["resultedAt"] = now_iso()


def advance_race(state: dict[str, Any], payload: dict[str, Any]) -> None:
    current = find_race(state, payload.get("raceNumber"))
    if current["status"] != "resulted":
        raise ApiError("Declare the result before moving on")
    next_number = int(current["raceNumber"]) + 1
    next_race = next((race for race in state["races"] if race["raceNumber"] == next_number), None)
    if next_race is None:
        state["event"]["status"] = "final"
        return
    if next_race["status"] == "pending":
        next_race["status"] = "open"
        next_race["openedAt"] = now_iso()
        next_race["bettingClosesAt"] = None
    state["event"]["currentRaceNumber"] = next_number
    state["event"]["status"] = "running"


def finalise_event(state: dict[str, Any], payload: dict[str, Any]) -> None:
    unfinished = [race["raceNumber"] for race in state["races"] if race["status"] != "resulted"]
    if unfinished and not payload.get("force"):
        raise ApiError("There are unfinished races")
    state["event"]["status"] = "final"


def reset_event_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "Mess Greyhound Night").strip() or "Mess Greyhound Night"
    starting_balance = bounded_int(
        payload.get("startingBalance", DEFAULT_STARTING_BALANCE),
        "Starting balance",
        minimum=1,
        maximum=10_000,
    )
    max_race_stake = bounded_int(
        payload.get("maxRaceStake", DEFAULT_MAX_RACE_STAKE),
        "Maximum race stake",
        minimum=1,
        maximum=10_000,
    )
    betting_countdown_seconds = bounded_int(
        payload.get("bettingCountdownSeconds", DEFAULT_BETTING_COUNTDOWN_SECONDS),
        "Betting countdown",
        minimum=1,
        maximum=3_600,
    )
    race_count = bounded_int(
        payload.get("raceCount", DEFAULT_RACE_COUNT),
        "Race count",
        minimum=1,
        maximum=30,
    )
    seed = payload.get("seed")
    numeric_seed = None if seed in {None, ""} else int(seed)
    return new_event_state(
        event_name=name[:100],
        starting_balance=starting_balance,
        max_race_stake=max_race_stake,
        betting_countdown_seconds=betting_countdown_seconds,
        race_count=race_count,
        seed=numeric_seed,
    )


def ledger_csv(state: dict[str, Any]) -> bytes:
    enriched = summarized_state(state)
    player_lookup = {player["id"]: player for player in enriched["players"]}
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "race",
            "status",
            "player_ref",
            "player",
            "trap",
            "dog",
            "stake",
            "winner_trap",
            "winner_dog",
            "payout",
            "final_balance",
        ]
    )
    for race in enriched["races"]:
        payouts_by_bet = {}
        for payout in race.get("payouts", []):
            split = payout["amount"] / max(1, len(payout.get("betIds", [])))
            for bet_id in payout.get("betIds", []):
                payouts_by_bet[bet_id] = split
        for bet in race["bets"]:
            player = player_lookup.get(bet["playerId"], {})
            writer.writerow(
                [
                    race["raceNumber"],
                    race["status"],
                    bet["playerReference"],
                    bet["playerName"],
                    bet["trap"],
                    bet["dogName"],
                    bet["stake"],
                    race.get("winningTrap") or "",
                    race.get("winningDog") or "",
                    payouts_by_bet.get(bet["id"], 0),
                    player.get("balance", ""),
                ]
            )
    return output.getvalue().encode("utf-8")


class RaceNightHandler(BaseHTTPRequestHandler):
    server_version = "MessRaceNight/1.0"

    post_routes: dict[str, Callable[[dict[str, Any], dict[str, Any]], None]] = {
        "/api/event/update": update_event,
        "/api/players/add": add_player,
        "/api/players/adjust": adjust_player,
        "/api/players/remove": remove_player,
        "/api/players/reset-pin": reset_player_pin,
        "/api/bets/place": place_bet,
        "/api/bets/void": void_bet,
        "/api/races/open": open_betting,
        "/api/races/start-countdown": start_countdown,
        "/api/races/close": close_betting,
        "/api/races/draw-video": draw_video,
        "/api/races/record-result": record_result,
        "/api/races/advance": advance_race,
        "/api/event/finalise": finalise_event,
        "/api/videos/add": add_video,
        "/api/videos/remove": remove_video,
    }

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "service": "mess-race-night", "dependencies": "standard-library"})
            return
        if parsed.path == "/api/state":
            with STATE_LOCK:
                state = load_state_unlocked()
                if apply_race_timers(state):
                    save_state_unlocked(state)
                self.send_json(summarized_state(state))
            return
        if parsed.path == "/api/admin/state":
            with STATE_LOCK:
                state = load_state_unlocked()
                if apply_race_timers(state):
                    save_state_unlocked(state)
                self.send_json(summarized_state(state, include_private=True))
            return
        if parsed.path == "/api/export/ledger.csv":
            with STATE_LOCK:
                state = load_state_unlocked()
                if apply_race_timers(state):
                    save_state_unlocked(state)
                self.send_bytes(ledger_csv(state), "text/csv; charset=utf-8", "mess-race-ledger.csv")
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/event/reset":
            try:
                payload = self.read_json()
                self.send_json(mutate_state(lambda _state: reset_event_from_payload(payload), include_private=True))
            except ApiError as exc:
                self.send_json({"error": str(exc)}, status=exc.status)
            except Exception as exc:
                self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/login":
            self.handle_login()
            return
        if parsed.path == "/api/punter/login":
            self.handle_punter_login()
            return
        if parsed.path == "/api/punter/state":
            self.handle_punter_state()
            return
        if parsed.path == "/api/punter/bet":
            self.handle_punter_bet()
            return

        route = self.post_routes.get(parsed.path)
        if route is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            payload = self.read_json()
            self.send_json(mutate_state(lambda state: route(state, payload), include_private=True))
        except ApiError as exc:
            self.send_json({"error": str(exc)}, status=exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def handle_punter_login(self) -> None:
        try:
            payload = self.read_json()
            with STATE_LOCK:
                state = load_state_unlocked()
                if apply_race_timers(state):
                    save_state_unlocked(state)
                player = authenticate_punter(state, payload)
                self.send_json(punter_summary(state, player))
        except ApiError as exc:
            self.send_json({"error": str(exc)}, status=exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def handle_login(self) -> None:
        try:
            payload = self.read_json()
            with STATE_LOCK:
                state = load_state_unlocked()
                if apply_race_timers(state):
                    save_state_unlocked(state)
                self.send_json(authenticate_login(state, payload))
        except ApiError as exc:
            self.send_json({"error": str(exc)}, status=exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def handle_punter_state(self) -> None:
        self.handle_punter_login()

    def handle_punter_bet(self) -> None:
        try:
            payload = self.read_json()
            with STATE_LOCK:
                state = load_state_unlocked()
                timer_changed = apply_race_timers(state)
                try:
                    player = place_punter_bet(state, payload)
                except Exception:
                    if timer_changed:
                        save_state_unlocked(state)
                    raise
                save_state_unlocked(state)
                self.send_json(punter_summary(state, player))
        except ApiError as exc:
            self.send_json({"error": str(exc)}, status=exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ApiError("Request body is too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        if length == 0:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ApiError("JSON payload must be an object")
        return payload

    def serve_static(self, path: str) -> None:
        if path in {"", "/", "/admin", "/display", "/punter"}:
            path = "/index.html"
        requested = (STATIC_DIR / path.lstrip("/")).resolve()
        try:
            requested.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        if not requested.exists() or not requested.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        data = requested.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(requested.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_bytes(self, payload: bytes, content_type: str, filename: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Disposition", f"attachment; filename={filename}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def parse_runtime() -> tuple[str, int]:
    return os.environ.get("RACE_HOST", os.environ.get("WSG_HOST", "127.0.0.1")), int(
        os.environ.get("RACE_PORT", os.environ.get("WSG_PORT", "8000"))
    )


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), RaceNightHandler)
    print(f"Mess Race Night running at http://{host}:{port}/admin")
    print(f"TV display available at http://{host}:{port}/display")
    print(f"Punter login available at http://{host}:{port}/punter")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Mess Race Night.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run(*parse_runtime())
