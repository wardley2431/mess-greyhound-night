const adminView = document.querySelector("#adminView");
const displayView = document.querySelector("#displayView");
const punterView = document.querySelector("#punterView");
const toast = document.querySelector("#toast");
const pathName = window.location.pathname;
const isDisplay = pathName.startsWith("/display");
const isAdmin = pathName.startsWith("/admin");
const isPunter = pathName === "/" || pathName.startsWith("/punter");

const els = {
  adminEventTitle: document.querySelector("#adminEventTitle"),
  eventForm: document.querySelector("#eventForm"),
  eventNameInput: document.querySelector("#eventNameInput"),
  startingBalanceInput: document.querySelector("#startingBalanceInput"),
  maxRaceStakeInput: document.querySelector("#maxRaceStakeInput"),
  adminLogoutButton: document.querySelector("#adminLogoutButton"),
  sideRace: document.querySelector("#sideRace"),
  sideStatus: document.querySelector("#sideStatus"),
  sidePlayers: document.querySelector("#sidePlayers"),
  sidePool: document.querySelector("#sidePool"),
  raceKicker: document.querySelector("#raceKicker"),
  raceTitle: document.querySelector("#raceTitle"),
  raceStatus: document.querySelector("#raceStatus"),
  openBettingButton: document.querySelector("#openBettingButton"),
  startCountdownButton: document.querySelector("#startCountdownButton"),
  closeBettingButton: document.querySelector("#closeBettingButton"),
  drawVideoButton: document.querySelector("#drawVideoButton"),
  resultForm: document.querySelector("#resultForm"),
  winnerTrapSelect: document.querySelector("#winnerTrapSelect"),
  declareResultButton: document.querySelector("#declareResultButton"),
  nextRaceButton: document.querySelector("#nextRaceButton"),
  finaliseButton: document.querySelector("#finaliseButton"),
  resetButton: document.querySelector("#resetButton"),
  raceCardTitle: document.querySelector("#raceCardTitle"),
  selectedVideoBadge: document.querySelector("#selectedVideoBadge"),
  dogGrid: document.querySelector("#dogGrid"),
  bettingStateLabel: document.querySelector("#bettingStateLabel"),
  betForm: document.querySelector("#betForm"),
  betPlayerSelect: document.querySelector("#betPlayerSelect"),
  trapSelector: document.querySelector("#trapSelector"),
  betStakeInput: document.querySelector("#betStakeInput"),
  playerForm: document.querySelector("#playerForm"),
  playerNameInput: document.querySelector("#playerNameInput"),
  playerCoinsInput: document.querySelector("#playerCoinsInput"),
  leaderLabel: document.querySelector("#leaderLabel"),
  playersTable: document.querySelector("#playersTable"),
  ledgerTitle: document.querySelector("#ledgerTitle"),
  poolLabel: document.querySelector("#poolLabel"),
  ledgerList: document.querySelector("#ledgerList"),
  historyList: document.querySelector("#historyList"),
  videoForm: document.querySelector("#videoForm"),
  videoTitleInput: document.querySelector("#videoTitleInput"),
  videoSourceInput: document.querySelector("#videoSourceInput"),
  videoWinnerInput: document.querySelector("#videoWinnerInput"),
  videoList: document.querySelector("#videoList"),
  videoLibraryStatus: document.querySelector("#videoLibraryStatus"),
  tvHeader: document.querySelector("#tvHeader"),
  tvKicker: document.querySelector("#tvKicker"),
  tvRaceTitle: document.querySelector("#tvRaceTitle"),
  tvStatus: document.querySelector("#tvStatus"),
  tvMain: document.querySelector("#tvMain"),
  tvRaceStage: document.querySelector("#tvRaceStage"),
  tvVideoStage: document.querySelector("#tvVideoStage"),
  tvDogs: document.querySelector("#tvDogs"),
  tvPool: document.querySelector("#tvPool"),
  tvBetCount: document.querySelector("#tvBetCount"),
  tvBigBets: document.querySelector("#tvBigBets"),
  tvLeaderboard: document.querySelector("#tvLeaderboard"),
  tvLeaderboardTicker: document.querySelector("#tvLeaderboardTicker"),
  finalBoard: document.querySelector("#finalBoard"),
  finalTitle: document.querySelector("#finalTitle"),
  finalLeaderboard: document.querySelector("#finalLeaderboard"),
  punterEventName: document.querySelector("#punterEventName"),
  punterLoginForm: document.querySelector("#punterLoginForm"),
  punterReferenceInput: document.querySelector("#punterReferenceInput"),
  punterPinInput: document.querySelector("#punterPinInput"),
  punterBetPanel: document.querySelector("#punterBetPanel"),
  punterRefLabel: document.querySelector("#punterRefLabel"),
  punterName: document.querySelector("#punterName"),
  punterBalance: document.querySelector("#punterBalance"),
  punterRaceRemaining: document.querySelector("#punterRaceRemaining"),
  punterRaceStatus: document.querySelector("#punterRaceStatus"),
  punterRaceTitle: document.querySelector("#punterRaceTitle"),
  punterRaceCardTitle: document.querySelector("#punterRaceCardTitle"),
  punterLogoutButton: document.querySelector("#punterLogoutButton"),
  punterDogs: document.querySelector("#punterDogs"),
  punterCurrentBets: document.querySelector("#punterCurrentBets"),
  punterLeaderboard: document.querySelector("#punterLeaderboard"),
  punterHistory: document.querySelector("#punterHistory"),
};

let state = null;
let punterState = null;
let selectedTrap = 1;
let busy = false;
const punterStorageKey = "messRacePunterLogin";
const adminStorageKey = "messRaceAdminLogin";

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 3200);
}

function coins(value) {
  return `${Number(value || 0).toLocaleString()} MC`;
}

function statusLabel(status) {
  const labels = {
    pending: "Pending",
    open: "Betting Open",
    closed: "Betting Closed",
    video: "Video Drawn",
    resulted: "Result Official",
  };
  return labels[status] || status || "-";
}

function secondsUntil(timestamp) {
  if (!timestamp) return null;
  const value = Date.parse(timestamp);
  if (Number.isNaN(value)) return null;
  return Math.max(0, Math.ceil((value - Date.now()) / 1000));
}

function countdownLabel(timestamp) {
  const seconds = secondsUntil(timestamp);
  if (seconds === null) return null;
  const minutes = Math.floor(seconds / 60);
  const remainder = String(seconds % 60).padStart(2, "0");
  return `${minutes}:${remainder}`;
}

function isBettingAccepting(race) {
  return race?.status === "open" && secondsUntil(race.bettingClosesAt) !== 0;
}

function raceStatusLabel(race) {
  if (race?.status === "open") {
    const countdown = countdownLabel(race.bettingClosesAt);
    if (countdown) return `Bets close in ${countdown}`;
  }
  return statusLabel(race?.status);
}

function setValueWhenIdle(element, value) {
  if (document.activeElement !== element) {
    element.value = value;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function currentRace() {
  return state?.currentRace || state?.races?.[0] || null;
}

function trapTotal(race, trap) {
  return race.totalsByTrap?.find((item) => item.trap === trap) || { stake: 0, bets: 0 };
}

function raceStakeLimit(source = state) {
  return Number(source?.event?.maxRaceStake || 10000);
}

function raceStakeForPlayer(race, playerId) {
  return race.bets
    .filter((bet) => bet.playerId === playerId)
    .reduce((total, bet) => total + Number(bet.stake || 0), 0);
}

function raceStakeRemaining(race, player, source = state) {
  if (!race || !player) return 0;
  const remainingLimit = raceStakeLimit(source) - raceStakeForPlayer(race, player.id);
  return Math.max(0, Math.min(Number(player.balance || 0), remainingLimit));
}

function greatestCommonDivisor(left, right) {
  let a = Math.abs(left);
  let b = Math.abs(right);
  while (b) {
    const next = a % b;
    a = b;
    b = next;
  }
  return a || 1;
}

function fractionLabel(numerator, denominator) {
  const divisor = greatestCommonDivisor(numerator, denominator);
  return `${numerator / divisor}/${denominator / divisor}`;
}

function toteReturn(race, trap) {
  const total = trapTotal(race, trap);
  if (!race.pool) return { label: "No pool", detail: "0 MC backed", multiplier: null };
  if (!total.stake) return { label: "No backers", detail: "0 MC backed", multiplier: null };
  const multiplier = race.pool / total.stake;
  return {
    label: fractionLabel(Number(race.pool), Number(total.stake)),
    detail: `${coins(total.stake)} backed`,
    multiplier,
  };
}

async function requestState() {
  const endpoint = isDisplay ? "/api/state" : "/api/admin/state";
  const response = await fetch(endpoint, { cache: "no-store" });
  const result = await response.json();
  if (!response.ok || result.error) {
    throw new Error(result.error || "State request failed");
  }
  state = result;
  render();
}

async function postAction(path, payload = {}) {
  if (busy) return;
  busy = true;
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok || result.error) {
      throw new Error(result.error || "Action failed");
    }
    state = result;
    render();
    return result;
  } catch (error) {
    showToast(error.message);
    return null;
  } finally {
    busy = false;
  }
}

function optionHtml(player) {
  return `<option value="${player.id}">#${player.reference} ${escapeHtml(player.name)} - ${coins(player.balance)}</option>`;
}

function renderPlayerOptions() {
  const activePlayers = state.players.filter((player) => player.active);
  const previousBetPlayer = els.betPlayerSelect.value;
  const options = activePlayers.length
    ? activePlayers.map(optionHtml).join("")
    : '<option value="">No players</option>';
  els.betPlayerSelect.innerHTML = options;

  if (activePlayers.some((player) => player.id === previousBetPlayer)) {
    els.betPlayerSelect.value = previousBetPlayer;
  }
}

function renderTrapSelector(race) {
  els.trapSelector.innerHTML = race.lineup
    .map((entry) => {
      const active = entry.trap === selectedTrap ? "active" : "";
      return `<button class="${active} trap-${entry.trap}" type="button" data-trap="${entry.trap}">${entry.trap}</button>`;
    })
    .join("");
}

function renderDogGrid(race) {
  els.dogGrid.innerHTML = race.lineup
    .map((entry) => {
      const total = trapTotal(race, entry.trap);
      const odds = toteReturn(race, entry.trap);
      const winner = race.winningTrap === entry.trap ? "winner" : "";
      return `
        <article class="dog-tile ${winner}">
          <div class="trap-box trap-${entry.trap}">Trap ${entry.trap}</div>
          <h4>${escapeHtml(entry.name)}</h4>
          <div class="dog-meta">
            <span>Age ${entry.age}</span>
            <strong class="odds-value">${odds.label}</strong>
          </div>
          <div class="bet-meter">
            <span style="width: ${Math.min(100, total.stake * 5)}%"></span>
          </div>
          <p>${odds.detail} - ${total.bets} bets</p>
        </article>
      `;
    })
    .join("");
}

function renderPlayers() {
  renderPlayerOptions();
  const leader = state.leaderboard[0];
  els.leaderLabel.textContent = leader ? `${leader.name} ${coins(leader.balance)}` : "-";
  els.playersTable.innerHTML = state.players
    .map((player) => {
      const inactive = player.active ? "" : " inactive";
      return `
        <tr class="${inactive}">
          <td>#${player.reference}</td>
          <td>${escapeHtml(player.name)}</td>
          <td><strong>${coins(player.balance)}</strong></td>
          <td>${coins(player.totalStaked)}</td>
          <td>${coins(player.totalWon)}</td>
          <td><button type="button" data-reset-pin="${player.id}">New PIN</button></td>
        </tr>
      `;
    })
    .join("") || '<tr><td colspan="6" class="empty-cell">No players yet</td></tr>';
}

function setAdminBetLimit(race) {
  const player = state.players.find((item) => item.id === els.betPlayerSelect.value);
  const remaining = raceStakeRemaining(race, player);
  const canPlace = isBettingAccepting(race) && player && remaining > 0;
  const submitButton = els.betForm.querySelector('button[type="submit"]');
  els.betStakeInput.max = remaining;
  els.betStakeInput.disabled = !canPlace;
  submitButton.disabled = !canPlace;
  if (canPlace && Number(els.betStakeInput.value) > remaining) {
    els.betStakeInput.value = remaining;
  }
}

function renderLedger(race) {
  els.ledgerTitle.textContent = `Race ${race.raceNumber} Bets`;
  els.poolLabel.textContent = coins(race.pool);
  if (!race.bets.length) {
    els.ledgerList.innerHTML = '<div class="empty-state">No bets recorded</div>';
    return;
  }
  const canVoid = !race.winningTrap;
  els.ledgerList.innerHTML = race.bets
    .slice()
    .reverse()
    .map((bet) => `
      <div class="ledger-row">
        <div>
          <strong>#${bet.playerReference} ${escapeHtml(bet.playerName)}</strong>
          <span>Trap ${bet.trap} - ${escapeHtml(bet.dogName)}</span>
        </div>
        <strong>${coins(bet.stake)}</strong>
        <button type="button" data-void-bet="${bet.id}" ${canVoid ? "" : "disabled"}>Void</button>
      </div>
    `)
    .join("");
}

function renderHistory() {
  els.historyList.innerHTML = state.races
    .map((race) => {
      const active = race.raceNumber === state.event.currentRaceNumber ? "active" : "";
      const result = race.winningTrap
        ? `Trap ${race.winningTrap} - ${escapeHtml(race.winningDog)}`
        : statusLabel(race.status);
      return `
        <div class="history-row ${active}">
          <strong>Race ${race.raceNumber}</strong>
          <span>${result}</span>
          <em>${coins(race.pool)}</em>
        </div>
      `;
    })
    .join("");
}

function renderVideoLibrary() {
  const videos = state.videoLibrary;
  const used = new Set(state.races.map((race) => race.selectedVideo?.id).filter(Boolean));
  els.videoLibraryStatus.textContent = `${videos.filter((video) => video.ready).length}/${videos.length} ready`;
  const key = JSON.stringify([videos, [...used]]);
  if (els.videoList.dataset.libraryKey === key || els.videoList.contains(document.activeElement)) return;
  els.videoList.dataset.libraryKey = key;
  els.videoList.innerHTML = videos
    .map((video) => {
      const source = video.source ? escapeHtml(video.source) : "No file linked";
      const canPreview = /^(https?:\/\/|\/videos\/)/.test(video.source || "");
      const sourceLink = canPreview
        ? `<a href="${escapeHtml(video.source)}" target="_blank" rel="noopener noreferrer">${source}</a>`
        : `<span>${source}</span>`;
      const options = Array.from({ length: 6 }, (_, index) => {
        const trap = index + 1;
        return `<option value="${trap}" ${video.winningTrap === trap ? "selected" : ""}>Trap ${trap}</option>`;
      }).join("");
      const locked = used.has(video.id) ? "disabled" : "";
      return `
        <div class="video-row">
          <div>
            <strong>${escapeHtml(video.title)}</strong>
            ${sourceLink}
            <span class="video-status" data-ready="${Boolean(video.ready)}">${escapeHtml(video.problem || "Ready")}</span>
          </div>
          <label class="video-winner">
            <span>Winning trap</span>
            <select data-video-winner="${video.id}" aria-label="Winning trap for ${escapeHtml(video.title)}" ${locked}>
              <option value="" ${video.winningTrap ? "" : "selected"} disabled>Not set</option>
              ${options}
            </select>
          </label>
          <button type="button" data-remove-video="${video.id}" ${locked}>Remove</button>
        </div>
      `;
    })
    .join("") || '<div class="empty-state">No videos in library</div>';
}

function renderAdmin() {
  const race = currentRace();
  if (!race) return;
  const activePlayers = state.players.filter((player) => player.active);
  const leader = state.leaderboard[0];
  const status = statusLabel(race.status);
  const liveStatus = raceStatusLabel(race);

  els.adminEventTitle.textContent = state.event.name;
  setValueWhenIdle(els.eventNameInput, state.event.name);
  setValueWhenIdle(els.startingBalanceInput, state.event.startingBalance);
  setValueWhenIdle(els.maxRaceStakeInput, raceStakeLimit());
  setValueWhenIdle(els.playerCoinsInput, state.event.startingBalance);
  els.sideRace.textContent = `${race.raceNumber}/${state.races.length}`;
  els.sideStatus.textContent = state.event.status === "final" ? "Final" : liveStatus;
  els.sidePlayers.textContent = activePlayers.length;
  els.sidePool.textContent = coins(state.totalCoinPool);
  els.raceTitle.textContent = `Race ${race.raceNumber}`;
  els.raceStatus.textContent = liveStatus;
  els.raceStatus.dataset.status = race.status;
  els.raceCardTitle.textContent = race.winningTrap
    ? `Winner: Trap ${race.winningTrap}`
    : "Six Dog Lineup";
  els.bettingStateLabel.textContent = `${liveStatus} - Max ${coins(raceStakeLimit())}`;

  const selected = race.selectedVideo;
  els.selectedVideoBadge.textContent = selected
    ? `${selected.title}${race.winningTrap ? ` - Trap ${race.winningTrap}` : ""}`
    : race.autoDrawError || "No video drawn";

  const isRaceOpen = race.status === "open";
  const isOpen = isBettingAccepting(race);
  const isCountdownRunning = Boolean(race.bettingClosesAt);
  const isClosed = race.status === "closed";
  const hasReadyVideo = state.videoLibrary.some((video) => video.ready);
  const isBlankDemoVideo = race.status === "video" && selected && !selected.source && !race.winningTrap;
  const isVideo = race.status === "video";
  const isResulted = race.status === "resulted";
  const isFinal = state.event.status === "final";
  els.openBettingButton.disabled = isFinal || !["pending", "closed"].includes(race.status) || selected || race.winningTrap;
  els.startCountdownButton.disabled = isFinal || !isRaceOpen || isCountdownRunning || selected || race.winningTrap || !hasReadyVideo;
  els.closeBettingButton.disabled = isFinal || !isRaceOpen;
  els.drawVideoButton.disabled = isFinal || !(isClosed || isBlankDemoVideo) || !hasReadyVideo;
  els.declareResultButton.disabled = isFinal || !isVideo || !selected?.source;
  els.nextRaceButton.disabled = isFinal || !isResulted;
  els.finaliseButton.disabled = !state.players.length;
  els.betForm.querySelectorAll("input, select, button").forEach((item) => {
    item.disabled = !isOpen || !activePlayers.length;
  });
  if (race.winningTrap) {
    els.winnerTrapSelect.value = String(race.winningTrap);
  } else if (selected) {
    els.winnerTrapSelect.value = "";
  }

  renderTrapSelector(race);
  renderDogGrid(race);
  renderPlayers();
  setAdminBetLimit(race);
  renderLedger(race);
  renderHistory();
  renderVideoLibrary();
  if (leader) {
    els.raceKicker.textContent = `Leader #${leader.reference} ${leader.name}`;
  } else {
    els.raceKicker.textContent = "Current Race";
  }
}

function videoMarkup(video) {
  if (!video?.source) {
    return `
      <div class="video-placeholder">
        <span>Video unavailable</span>
      </div>
    `;
  }
  return `
    <video src="${escapeHtml(video.source)}" autoplay muted playsinline controls preload="auto"></video>
    <div class="video-feedback" role="status" hidden>
      <span></span>
      <button type="button" hidden></button>
    </div>
  `;
}

function setVideoStage(html, key = "") {
  if (els.tvVideoStage.dataset.stageKey === key) return;
  els.tvVideoStage.dataset.stageKey = key;
  els.tvVideoStage.innerHTML = html;
  wireDisplayVideo();
}

function showVideoFeedback(message, action = "") {
  const feedback = els.tvVideoStage.querySelector(".video-feedback");
  if (!feedback) return;
  feedback.hidden = !message;
  feedback.querySelector("span").textContent = message;
  const button = feedback.querySelector("button");
  button.hidden = !action;
  button.textContent = action;
}

function wireDisplayVideo() {
  const video = els.tvVideoStage.querySelector("video");
  if (!video) return;
  video.addEventListener("playing", () => showVideoFeedback(""));
  video.addEventListener("waiting", () => showVideoFeedback("Loading video"));
  video.addEventListener("error", () => {
    const messages = {
      2: "Video download failed",
      3: "Video could not be decoded",
      4: "Video file or format is unavailable",
    };
    showVideoFeedback(messages[video.error?.code] || "Video unavailable", "Retry video");
  });
  els.tvVideoStage.querySelector(".video-feedback button").addEventListener("click", () => {
    if (video.error) video.load();
    delete video.dataset.playAttempted;
    playDisplayVideo();
  });
}

function playDisplayVideo() {
  const video = els.tvVideoStage.querySelector("video");
  if (!video || video.ended || video.error || video.dataset.playAttempted) return;
  video.dataset.playAttempted = "true";
  video.muted = true;
  video.play().catch((error) => {
    if (error.name === "AbortError" || video.error) return;
    showVideoFeedback("Playback paused", "Play race");
  });
}

function renderTvDogs(race) {
  els.tvDogs.innerHTML = race.lineup
    .map((entry) => {
      const total = trapTotal(race, entry.trap);
      const odds = toteReturn(race, entry.trap);
      const winner = race.winningTrap === entry.trap ? "winner" : "";
      return `
        <article class="tv-dog ${winner}">
          <div class="tv-trap trap-${entry.trap}">${entry.trap}</div>
          <div>
            <h2>${escapeHtml(entry.name)}</h2>
            <span>Age ${entry.age} - ${odds.detail}</span>
          </div>
          <strong title="${escapeHtml(odds.label)}">${odds.multiplier === null ? "--" : escapeHtml(odds.label)}</strong>
        </article>
      `;
    })
    .join("");
}

function renderTvBigBets(race) {
  const biggestBets = race.bets
    .slice()
    .sort((left, right) => {
      if (right.stake !== left.stake) return right.stake - left.stake;
      return left.playerName.localeCompare(right.playerName);
    })
    .slice(0, 5);

  els.tvBigBets.innerHTML = biggestBets
    .map((bet, index) => `
      <div class="tv-bet-row">
        <span>${index + 1}</span>
        <div>
          <strong>${escapeHtml(bet.playerName)}</strong>
          <em>Punter #${bet.playerReference} - Trap ${bet.trap} - ${escapeHtml(bet.dogName)}</em>
        </div>
        <b>${coins(bet.stake)}</b>
      </div>
    `)
    .join("") || '<div class="tv-empty">No bets yet</div>';
}

function renderTvLeaderboard(target, options = {}) {
  const players = state.leaderboard.slice(0, 10);
  const items = players
    .map((player, index) => `
      <li>
        <small>${index + 1}</small>
        <span>#${player.reference} ${escapeHtml(player.name)}</span>
        <strong>${coins(player.balance)}</strong>
      </li>
    `)
    .join("") || "<li><small>-</small><span>No players</span><strong>0 MC</strong></li>";

  target.innerHTML = options.ticker && players.length > 1 ? items + items : items;
  if (options.ticker) {
    target.style.setProperty("--ticker-duration", `${Math.max(28, players.length * 5)}s`);
  }
}

function renderDisplay() {
  const race = currentRace();
  if (!race) return;
  const showRaceVideo = state.event.status !== "final" && race.status === "video" && race.selectedVideo;

  els.tvKicker.textContent = state.event.name;
  els.tvRaceTitle.textContent = `Race ${race.raceNumber}`;
  els.tvHeader.hidden = showRaceVideo;
  const hideTvStatus = showRaceVideo;
  els.tvStatus.hidden = hideTvStatus;
  els.tvStatus.textContent = hideTvStatus
    ? ""
    : state.event.status === "final"
      ? "Final Standings"
      : raceStatusLabel(race);
  els.tvStatus.dataset.status = race.status;
  els.tvPool.textContent = coins(race.pool);
  els.tvBetCount.textContent = `${race.bets.length.toLocaleString()} bets`;
  renderTvLeaderboard(els.tvLeaderboard, { ticker: true });
  renderTvDogs(race);
  renderTvBigBets(race);

  if (state.event.status === "final") {
    els.tvMain.hidden = true;
    els.finalBoard.hidden = false;
    els.finalTitle.textContent = state.event.name;
    renderTvLeaderboard(els.finalLeaderboard);
    return;
  }

  els.tvMain.hidden = false;
  els.finalBoard.hidden = true;
  if (race.winningTrap) {
    setVideoStage(`
      <div class="winner-splash">
        <span>Winner</span>
        <strong>Trap ${race.winningTrap}</strong>
        <em>${escapeHtml(race.winningDog)}</em>
      </div>
    `, `winner-${race.raceNumber}-${race.winningTrap}`);
  } else if (race.status === "video" && race.selectedVideo) {
    setVideoStage(
      videoMarkup(race.selectedVideo),
      `video-${race.raceNumber}-${race.selectedVideo.id}-${race.selectedVideo.source || ""}`,
    );
    playDisplayVideo();
  } else {
    setVideoStage(`
      <div class="video-placeholder">
        <span>${escapeHtml(raceStatusLabel(race))}</span>
      </div>
    `, `status-${race.raceNumber}-${race.status}-${race.bettingClosesAt || ""}-${raceStatusLabel(race)}`);
  }
}

function getPunterCredentials() {
  try {
    const parsed = JSON.parse(localStorage.getItem(punterStorageKey) || "null");
    if (!parsed?.reference || !parsed?.pin) return null;
    return { reference: parsed.reference, pin: parsed.pin };
  } catch {
    return null;
  }
}

function setPunterCredentials(reference, pin) {
  localStorage.setItem(punterStorageKey, JSON.stringify({ reference, pin }));
}

function clearPunterCredentials() {
  localStorage.removeItem(punterStorageKey);
  punterState = null;
  els.punterLoginForm.hidden = false;
  els.punterBetPanel.hidden = true;
}

function hasAdminLogin() {
  return localStorage.getItem(adminStorageKey) === "true";
}

function setAdminLogin() {
  localStorage.setItem(adminStorageKey, "true");
}

function clearAdminLogin() {
  localStorage.removeItem(adminStorageKey);
}

async function requestLogin(payload) {
  const response = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok || result.error) throw new Error(result.error || "Login failed");
  return result;
}

async function requestPunterPublicHeader() {
  const response = await fetch("/api/state", { cache: "no-store" });
  const result = await response.json();
  if (!response.ok || result.error) throw new Error(result.error || "State request failed");
  els.punterEventName.textContent = result.event.name;
}

async function postPunter(path, payload = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok || result.error) throw new Error(result.error || "Punter request failed");
  punterState = result;
  renderPunter();
}

async function requestPunterState() {
  const credentials = getPunterCredentials();
  if (!credentials) {
    clearPunterCredentials();
    return;
  }
  try {
    await postPunter("/api/punter/state", credentials);
  } catch (error) {
    clearPunterCredentials();
    showToast(error.message);
  }
}

function renderPunterDogs(race, canBet, remaining) {
  els.punterDogs.innerHTML = race.lineup
    .map((entry) => {
      const odds = toteReturn(race, entry.trap);
      const winner = race.winningTrap === entry.trap ? "winner" : "";
      return `
        <article class="punter-dog ${winner}">
          <div class="tv-trap trap-${entry.trap}">${entry.trap}</div>
          <div>
            <h3>${escapeHtml(entry.name)}</h3>
            <span>${odds.label} - ${odds.detail}</span>
          </div>
          <form class="punter-dog-bet" data-punter-trap="${entry.trap}">
            <input
              name="stake"
              type="number"
              min="1"
              max="${Math.max(0, Number(remaining))}"
              step="1"
              inputmode="numeric"
              value="1"
              aria-label="Stake for Trap ${entry.trap}"
              ${canBet ? "" : "disabled"}
            >
            <button class="primary" type="submit" ${canBet ? "" : "disabled"}>Bet</button>
          </form>
        </article>
      `;
    })
    .join("");
}

function renderPunterCurrentBets() {
  const bets = punterState.myCurrentBets || [];
  els.punterCurrentBets.innerHTML = bets
    .slice()
    .reverse()
    .map((bet) => `
      <div class="punter-row">
        <span>Trap ${bet.trap} - ${escapeHtml(bet.dogName)}</span>
        <strong>${coins(bet.stake)}</strong>
      </div>
    `)
    .join("") || '<div class="empty-state">No bets this race</div>';
}

function renderPunterHistory() {
  const summaries = punterState.myRaceSummaries || [];
  els.punterHistory.innerHTML = summaries
    .slice()
    .reverse()
    .map((item) => {
      const result = item.winningTrap
        ? `Trap ${item.winningTrap} - ${escapeHtml(item.winningDog)}`
        : statusLabel(item.status);
      return `
        <div class="punter-row history">
          <span>Race ${item.raceNumber}: ${result}</span>
          <strong>${coins(item.staked)} / ${coins(item.payout)}</strong>
        </div>
      `;
    })
    .join("") || '<div class="empty-state">No race history yet</div>';
}

function renderPunterLeaderboard() {
  const players = (punterState.leaderboard || []).slice(0, 10);
  els.punterLeaderboard.innerHTML = players.length
    ? players
        .map((player, index) => `
          <li>
            <small>${index + 1}</small>
            <span>#${player.reference} ${escapeHtml(player.name)}</span>
            <strong>${coins(player.balance)}</strong>
          </li>
        `)
        .join("")
    : '<li><small>-</small><span>No players</span><strong>0 MC</strong></li>';
}

function renderPunter() {
  if (!punterState) return;
  const race = punterState.currentRace;
  const player = punterState.player;
  const remaining = raceStakeRemaining(race, player, punterState);
  const canBet = isBettingAccepting(race) && remaining > 0 && punterState.event.status !== "final";

  els.punterLoginForm.hidden = true;
  els.punterBetPanel.hidden = false;
  els.punterEventName.textContent = punterState.event.name;
  els.punterRefLabel.textContent = `Punter #${player.reference}`;
  els.punterName.textContent = player.name;
  els.punterBalance.textContent = coins(player.balance);
  els.punterRaceRemaining.textContent = coins(remaining);
  els.punterRaceStatus.textContent = punterState.event.status === "final" ? "Final Standings" : raceStatusLabel(race);
  els.punterRaceStatus.dataset.status = race.status;
  els.punterRaceTitle.textContent = `Race ${race.raceNumber}`;
  els.punterRaceCardTitle.textContent = `Race ${race.raceNumber} Runners`;

  renderPunterDogs(race, canBet, remaining);
  renderPunterCurrentBets();
  renderPunterLeaderboard();
  renderPunterHistory();
}

function render() {
  if (!state) return;
  if (isDisplay) {
    renderDisplay();
  } else if (isPunter) {
    renderPunter();
  } else {
    renderAdmin();
  }
}

function wireAdminEvents() {
  els.eventForm.addEventListener("submit", (event) => {
    event.preventDefault();
    postAction("/api/event/update", {
      name: els.eventNameInput.value,
      startingBalance: Number(els.startingBalanceInput.value),
      maxRaceStake: Number(els.maxRaceStakeInput.value),
    });
  });

  els.openBettingButton.addEventListener("click", () => {
    postAction("/api/races/open", { raceNumber: currentRace()?.raceNumber });
  });
  els.startCountdownButton.addEventListener("click", () => {
    postAction("/api/races/start-countdown", { raceNumber: currentRace()?.raceNumber });
  });
  els.closeBettingButton.addEventListener("click", () => {
    postAction("/api/races/close", { raceNumber: currentRace()?.raceNumber });
  });
  els.drawVideoButton.addEventListener("click", () => {
    postAction("/api/races/draw-video", { raceNumber: currentRace()?.raceNumber });
  });
  els.resultForm.addEventListener("submit", (event) => {
    event.preventDefault();
    postAction("/api/races/record-result", {
      raceNumber: currentRace()?.raceNumber,
      winningTrap: els.winnerTrapSelect.value,
    });
  });
  els.nextRaceButton.addEventListener("click", () => {
    postAction("/api/races/advance", { raceNumber: currentRace()?.raceNumber });
  });
  els.finaliseButton.addEventListener("click", () => {
    const unfinished = state.races.some((race) => race.status !== "resulted");
    if (unfinished && !window.confirm("Show the final leaderboard before every race has a result?")) return;
    postAction("/api/event/finalise", { force: unfinished });
  });

  els.betForm.addEventListener("submit", (event) => {
    event.preventDefault();
    postAction("/api/bets/place", {
      raceNumber: currentRace()?.raceNumber,
      playerId: els.betPlayerSelect.value,
      trap: selectedTrap,
      stake: Number(els.betStakeInput.value),
    });
  });

  els.betPlayerSelect.addEventListener("change", () => {
    setAdminBetLimit(currentRace());
  });

  els.trapSelector.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-trap]");
    if (!button) return;
    selectedTrap = Number(button.dataset.trap);
    renderTrapSelector(currentRace());
  });

  els.playerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const previousIds = new Set(state.players.map((player) => player.id));
    postAction("/api/players/add", {
      name: els.playerNameInput.value,
      startingBalance: Number(els.playerCoinsInput.value || state.event.startingBalance),
    }).then((result) => {
      if (!result) return;
      const player = result.players.find((item) => !previousIds.has(item.id));
      if (player) {
        showToast(`Added #${player.reference} ${player.name}. PIN ${player.pin}`);
      }
      els.playerNameInput.value = "";
    });
  });

  els.playersTable.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-reset-pin]");
    if (!button) return;
    postAction("/api/players/reset-pin", { playerId: button.dataset.resetPin }).then((result) => {
      const player = result?.players.find((item) => item.id === button.dataset.resetPin);
      if (player) {
        showToast(`New PIN for #${player.reference} ${player.name}: ${player.pin}`);
      }
    });
  });

  els.ledgerList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-void-bet]");
    if (!button) return;
    postAction("/api/bets/void", {
      raceNumber: currentRace()?.raceNumber,
      betId: button.dataset.voidBet,
    });
  });

  els.videoForm.addEventListener("submit", (event) => {
    event.preventDefault();
    postAction("/api/videos/add", {
      title: els.videoTitleInput.value,
      source: els.videoSourceInput.value,
      winningTrap: Number(els.videoWinnerInput.value),
    }).then(() => {
      els.videoTitleInput.value = "";
      els.videoSourceInput.value = "";
    });
  });

  els.videoList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-remove-video]");
    if (!button) return;
    postAction("/api/videos/remove", { videoId: button.dataset.removeVideo });
  });

  els.videoList.addEventListener("change", (event) => {
    const select = event.target.closest("select[data-video-winner]");
    if (!select || !select.value) return;
    select.disabled = true;
    postAction("/api/videos/update", {
      videoId: select.dataset.videoWinner,
      winningTrap: Number(select.value),
    }).finally(() => {
      select.disabled = false;
      els.videoList.dataset.libraryKey = "";
    });
  });

  els.resetButton.addEventListener("click", () => {
    if (!window.confirm("Reset the night and clear all players, bets, and results?")) return;
    postAction("/api/event/reset", {
      name: els.eventNameInput.value || state.event.name,
      startingBalance: Number(els.startingBalanceInput.value || state.event.startingBalance),
      maxRaceStake: Number(els.maxRaceStakeInput.value || raceStakeLimit()),
      raceCount: state.races.length || 10,
    });
  });

  els.adminLogoutButton.addEventListener("click", () => {
    clearAdminLogin();
    window.location.href = "/";
  });
}

function wirePunterEvents() {
  els.punterLoginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const reference = els.punterReferenceInput.value.trim();
    const pin = els.punterPinInput.value.trim();
    try {
      const result = await requestLogin({ reference, pin });
      if (result.role === "admin") {
        setAdminLogin();
        clearPunterCredentials();
        window.location.href = "/admin";
        return;
      }
      if (result.role !== "punter") {
        throw new Error("Login failed");
      }
      setPunterCredentials(Number(reference), pin);
      punterState = result.punter;
      if (!window.location.pathname.startsWith("/punter")) {
        window.location.href = "/punter";
        return;
      }
      renderPunter();
    } catch (error) {
      clearPunterCredentials();
      showToast(error.message);
    }
  });

  els.punterDogs.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-punter-trap]");
    if (!form) return;
    event.preventDefault();
    const credentials = getPunterCredentials();
    if (!credentials) {
      clearPunterCredentials();
      return;
    }
    try {
      await postPunter("/api/punter/bet", {
        ...credentials,
        raceNumber: punterState?.currentRace?.raceNumber,
        trap: Number(form.dataset.punterTrap),
        stake: Number(form.elements.stake.value),
      });
    } catch (error) {
      showToast(error.message);
    }
  });

  els.punterLogoutButton.addEventListener("click", () => {
    clearPunterCredentials();
    els.punterPinInput.value = "";
  });
}

async function boot() {
  if (isAdmin && !hasAdminLogin()) {
    window.location.replace("/");
    return;
  }

  adminView.hidden = !isAdmin;
  displayView.hidden = !isDisplay;
  punterView.hidden = !isPunter;

  if (isPunter) {
    wirePunterEvents();
    await requestPunterPublicHeader();
    const credentials = getPunterCredentials();
    if (credentials) {
      if (window.location.pathname === "/") {
        window.location.replace("/punter");
        return;
      }
      els.punterReferenceInput.value = credentials.reference;
      await requestPunterState();
    }
    setInterval(() => {
      requestPunterPublicHeader().catch(() => {});
      if (getPunterCredentials()) {
        requestPunterState().catch((error) => showToast(error.message));
      }
    }, 1000);
    return;
  }

  if (isAdmin) {
    wireAdminEvents();
  }
  await requestState();
  setInterval(() => {
    requestState().catch((error) => showToast(error.message));
  }, isDisplay || isAdmin ? 1000 : 2500);
}

boot().catch((error) => showToast(error.message));
