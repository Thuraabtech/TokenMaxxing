const messagesEl = document.getElementById("messages");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const vaultAmountEl = document.getElementById("vault-amount");
const vaultCardEl = document.querySelector(".vault-card");
const vaultCoinEl = document.querySelector(".vault-figure .coin");
const vaultFigureEl = document.querySelector(".vault-figure");

const TIER_LABELS = { low: "copper", medium: "silver", high: "gold" };
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let displayedSaved = 0;

function fmt(n) {
  return `$${n.toFixed(6)}`;
}

function addMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  wrap.innerHTML = `<div class="role">${role}</div><div class="bubble"></div>`;
  wrap.querySelector(".bubble").textContent = text;
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return wrap;
}

const THINKING_STAGES = [
  "Reading your question…",
  "Grading complexity…",
  "Routing to a tier…",
  "Minting your answer…",
];
const THINKING_STEADY = "Still working — bigger requests can take a minute or two…";

function addThinkingMessage() {
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";
  wrap.innerHTML = `
    <div class="role">assistant</div>
    <div class="bubble">
      <div class="thinking">
        <span class="coin coin-sm thinking-coin" aria-hidden="true"></span>
        <span class="stage-text mono">${THINKING_STAGES[0]}</span>
      </div>
    </div>
  `;
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  const stageEl = wrap.querySelector(".stage-text");
  let tick = 0;
  let intervalId = null;

  if (!reduceMotion && stageEl) {
    intervalId = setInterval(() => {
      tick += 1;
      stageEl.textContent =
        tick >= THINKING_STAGES.length * 2 ? THINKING_STEADY : THINKING_STAGES[tick % THINKING_STAGES.length];
    }, 1700);
  }

  return {
    wrap,
    stop() {
      if (intervalId) clearInterval(intervalId);
    },
  };
}

function renderSubtaskStrip(container, subtasks, totalSaved) {
  const strip = document.createElement("div");
  strip.className = "subtask-strip";
  subtasks.forEach((s) => {
    const label = TIER_LABELS[s.tier_used] || s.tier_used;
    const chip = document.createElement("span");
    chip.className = `tier-chip ${label}`;
    const escNote = s.escalated_from
      ? ` <span class="esc">(↑ from ${TIER_LABELS[s.escalated_from]})</span>`
      : "";
    chip.innerHTML = `${label}${escNote}`;
    strip.appendChild(chip);
  });
  container.appendChild(strip);

  if (totalSaved > 0) {
    const toast = document.createElement("div");
    toast.className = "save-toast";
    toast.innerHTML = `<span class="coin coin-sm"></span> saved ${fmt(totalSaved)} vs. all-Gold`;
    container.appendChild(toast);
  }
}

function spawnSparkles(container, count = 8) {
  if (reduceMotion || !container) return;
  for (let i = 0; i < count; i++) {
    const s = document.createElement("span");
    s.className = "spark";
    const angle = (Math.PI * 2 * i) / count + Math.random() * 0.5;
    const dist = 30 + Math.random() * 24;
    s.style.setProperty("--dx", `${Math.cos(angle) * dist}px`);
    s.style.setProperty("--dy", `${Math.sin(angle) * dist}px`);
    s.style.animationDelay = `${Math.random() * 0.1}s`;
    container.appendChild(s);
    setTimeout(() => s.remove(), 1000);
  }
}

function animateVaultTo(target) {
  if (reduceMotion) {
    displayedSaved = target;
    vaultAmountEl.textContent = fmt(target);
    return;
  }
  const start = displayedSaved;
  const delta = target - start;
  const duration = 700;
  const startTime = performance.now();

  function tick(now) {
    const t = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    const value = start + delta * eased;
    vaultAmountEl.textContent = fmt(value);
    if (t < 1) {
      requestAnimationFrame(tick);
    } else {
      displayedSaved = target;
    }
  }
  requestAnimationFrame(tick);

  vaultCoinEl.classList.add("drop");
  vaultCardEl.classList.add("pulse");
  setTimeout(() => vaultCoinEl.classList.remove("drop"), 400);
  setTimeout(() => vaultCardEl.classList.remove("pulse"), 900);
  if (delta > 0) spawnSparkles(vaultFigureEl);
}

function updateTierBars(tierCalls) {
  const total = Math.max(tierCalls.low + tierCalls.medium + tierCalls.high, 1);
  const barsEl = document.getElementById("tier-bars");
  barsEl.innerHTML = "";
  [["low", "Copper", tierCalls.low], ["medium", "Silver", tierCalls.medium], ["high", "Gold", tierCalls.high]].forEach(
    ([key, label, count]) => {
      const pct = Math.round((count / total) * 100);
      const row = document.createElement("div");
      row.className = "bar-row";
      row.innerHTML = `
        <div class="label"><span>${label}</span><span>${count}</span></div>
        <div class="bar-track"><div class="bar-fill ${key}" style="width:${pct}%"></div></div>
      `;
      barsEl.appendChild(row);
    }
  );
}

function updateLastRequest(data) {
  const sources = data.retrieved_sources.length ? data.retrieved_sources.join(", ") : "none";
  document.getElementById("last-request").innerHTML = `
    <div class="stat-row"><span>Sub-tasks</span><span class="val">${data.subtasks.length}</span></div>
    <div class="stat-row"><span>Cost</span><span class="val">${fmt(data.total_cost_usd)}</span></div>
    <div class="stat-row"><span>Saved</span><span class="val">${fmt(data.total_saved_usd)}</span></div>
    <div class="stat-row"><span>Sources</span><span class="val">${sources}</span></div>
  `;
}

async function fetchCostSummary() {
  const res = await fetch("/api/cost-summary");
  return res.json();
}

async function refreshCostSummary() {
  const data = await fetchCostSummary();
  displayedSaved = data.running_saved_usd;
  vaultAmountEl.textContent = fmt(data.running_saved_usd);
  updateTierBars(data.tier_calls);
}

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    input.value = chip.dataset.prompt;
    input.focus();
  });
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  document.getElementById("empty-state")?.remove();
  addMessage("user", message);
  input.value = "";
  sendBtn.disabled = true;

  const thinking = addThinkingMessage();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(body || res.statusText);
    }
    const data = await res.json();

    thinking.stop();
    thinking.wrap.querySelector(".bubble").textContent = data.answer;
    renderSubtaskStrip(thinking.wrap, data.subtasks, data.total_saved_usd);
    animateVaultTo(data.running_saved_usd);
    updateTierBars((await fetchCostSummary()).tier_calls);
    updateLastRequest(data);
  } catch (err) {
    thinking.stop();
    thinking.wrap.querySelector(".bubble").textContent = `Error: ${err.message}`;
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

// --- theme toggle ---
const themeToggle = document.getElementById("theme-toggle");
const storedTheme = localStorage.getItem("tokenmaxxer-theme");
if (storedTheme) document.documentElement.setAttribute("data-theme", storedTheme);

themeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme")
    || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("tokenmaxxer-theme", next);
});

// --- tier card 3D tilt + glare ---
if (!reduceMotion && window.matchMedia("(pointer: fine)").matches) {
  document.querySelectorAll(".tier-card").forEach((card) => {
    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width;
      const py = (e.clientY - rect.top) / rect.height;
      const rx = (0.5 - py) * 10;
      const ry = (px - 0.5) * 10;
      card.style.setProperty("--rx", `${rx}deg`);
      card.style.setProperty("--ry", `${ry}deg`);
      card.style.setProperty("--mx", `${px * 100}%`);
      card.style.setProperty("--my", `${py * 100}%`);
    });
    card.addEventListener("mouseleave", () => {
      card.style.setProperty("--rx", "0deg");
      card.style.setProperty("--ry", "0deg");
    });
  });
}

// --- scroll-reveal entrances ---
const revealEls = document.querySelectorAll(".reveal, .tier-card");
if (reduceMotion) {
  revealEls.forEach((el) => el.classList.add("in-view"));
} else {
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );
  revealEls.forEach((el) => io.observe(el));
}

refreshCostSummary();
