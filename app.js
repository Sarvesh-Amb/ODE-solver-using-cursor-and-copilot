const form = document.querySelector("#solver-form");
const statusLine = document.querySelector("#form-status");
const button = document.querySelector(".solve-button");
const canvas = document.querySelector("#solution-chart");
const context = canvas.getContext("2d");
const chartEmpty = document.querySelector("#chart-empty");
const numberFormat = new Intl.NumberFormat(undefined, { maximumSignificantDigits: 8 });
let plottedPoints = [];

const methodDescriptions = {
  Euler: "Forward Euler · local error O(h²)",
  Heun: "Improved Euler · local error O(h³)",
  RK4: "Fourth-order Runge–Kutta · local error O(h⁵)",
};

function showStatus(message, isError = false) {
  statusLine.textContent = message;
  statusLine.classList.toggle("error", isError);
}

function format(value) {
  return numberFormat.format(value);
}

function drawChart() {
  const bounds = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(bounds.width * ratio);
  canvas.height = Math.round(bounds.height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, bounds.width, bounds.height);
  if (plottedPoints.length === 0) return;

  const padding = { top: 16, right: 20, bottom: 28, left: 55 };
  const plotWidth = bounds.width - padding.left - padding.right;
  const plotHeight = bounds.height - padding.top - padding.bottom;
  const times = plottedPoints.map((point) => point.t);
  const values = plottedPoints.map((point) => point.y);
  const tMin = Math.min(...times);
  const tMax = Math.max(...times);
  let yMin = Math.min(...values);
  let yMax = Math.max(...values);
  if (yMin === yMax) {
    const margin = Math.max(Math.abs(yMin) * 0.1, 1);
    yMin -= margin;
    yMax += margin;
  } else {
    const margin = (yMax - yMin) * 0.1;
    yMin -= margin;
    yMax += margin;
  }
  const x = (time) => padding.left + (tMax === tMin ? plotWidth / 2 : (time - tMin) / (tMax - tMin) * plotWidth);
  const y = (value) => padding.top + (yMax - value) / (yMax - yMin) * plotHeight;

  context.font = "10px 'DM Mono', monospace";
  context.fillStyle = "#7e8982";
  context.strokeStyle = "rgba(57, 82, 66, .16)";
  context.lineWidth = 1;
  for (let tick = 0; tick <= 4; tick += 1) {
    const yPosition = padding.top + plotHeight * tick / 4;
    const value = yMax - (yMax - yMin) * tick / 4;
    context.beginPath();
    context.moveTo(padding.left, yPosition);
    context.lineTo(bounds.width - padding.right, yPosition);
    context.stroke();
    context.textAlign = "right";
    context.textBaseline = "middle";
    context.fillText(format(value), padding.left - 9, yPosition);
  }
  for (let tick = 0; tick <= 4; tick += 1) {
    const time = tMin + (tMax - tMin) * tick / 4;
    const xPosition = padding.left + plotWidth * tick / 4;
    context.beginPath();
    context.moveTo(xPosition, padding.top);
    context.lineTo(xPosition, padding.top + plotHeight);
    context.stroke();
    context.textAlign = tick === 0 ? "left" : tick === 4 ? "right" : "center";
    context.textBaseline = "top";
    context.fillText(format(time), xPosition, padding.top + plotHeight + 8);
  }

  context.beginPath();
  plottedPoints.forEach((point, index) => {
    const xPosition = x(point.t);
    const yPosition = y(point.y);
    if (index === 0) context.moveTo(xPosition, yPosition);
    else context.lineTo(xPosition, yPosition);
  });
  context.strokeStyle = "#167c5a";
  context.lineWidth = 2.5;
  context.lineJoin = "round";
  context.lineCap = "round";
  context.stroke();
  const first = plottedPoints[0];
  const last = plottedPoints[plottedPoints.length - 1];
  for (const point of [first, last]) {
    context.beginPath();
    context.arc(x(point.t), y(point.y), 3.5, 0, Math.PI * 2);
    context.fillStyle = "#dd654d";
    context.fill();
  }
}

function renderTable(points) {
  const body = document.querySelector("#results-body");
  const fragment = document.createDocumentFragment();
  points.forEach((point, index) => {
    const row = document.createElement("tr");
    for (const value of [index, format(point.t), format(point.y)]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    fragment.append(row);
  });
  body.replaceChildren(fragment);
}

form.addEventListener("change", (event) => {
  if (event.target.name === "method") {
    document.querySelector("#method-description").textContent = methodDescriptions[event.target.value];
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = new FormData(form);
  const payload = Object.fromEntries(values.entries());
  for (const key of ["t0", "y0", "t_end", "steps"]) payload[key] = Number(payload[key]);
  button.disabled = true;
  showStatus("Computing solution…");
  try {
    const response = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The solver could not complete this problem.");

    plottedPoints = result.points;
    chartEmpty.classList.add("hidden");
    document.querySelector("#final-value").textContent = format(plottedPoints.at(-1).y);
    document.querySelector("#step-size").textContent = format((payload.t_end - payload.t0) / payload.steps);
    document.querySelector("#sample-count").textContent = String(plottedPoints.length);
    document.querySelector("#chart-equation").textContent = `y′ = ${payload.expression}`;
    document.querySelector("#table-caption").textContent = `${payload.method} · ${payload.steps} intervals`;
    renderTable(plottedPoints);
    drawChart();
    showStatus(`Solved with ${payload.method}.`);
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
});

window.addEventListener("resize", drawChart);