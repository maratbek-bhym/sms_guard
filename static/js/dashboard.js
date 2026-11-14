/* Графики Dashboard. Данные приходят через json_script (экранируются Django), не через inline-код. */
(function () {
  var el = document.getElementById("chart-data");
  if (!el || typeof Chart === "undefined") return;
  var d = JSON.parse(el.textContent);
  var css = getComputedStyle(document.documentElement);
  var c = function (n) { return css.getPropertyValue(n).trim(); };
  Chart.defaults.font.family = '"IBM Plex Sans", system-ui, sans-serif';
  Chart.defaults.color = c("--muted");

  var days = d.per_day;
  new Chart(document.getElementById("chart-days"), {
    type: "bar",
    data: {
      labels: days.map(function (x) { return x.date.slice(8, 10) + "." + x.date.slice(5, 7); }),
      datasets: [{ label: "Проверок", data: days.map(function (x) { return x.count; }), backgroundColor: c("--ink-2"), borderRadius: 3, maxBarThickness: 22 }]
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#e4eae8" } }, x: { grid: { display: false } } }
    }
  });

  var cat = d.by_category;
  new Chart(document.getElementById("chart-cat"), {
    type: "doughnut",
    data: {
      labels: ["Безопасно", "Подозрительно", "Мошенничество"],
      datasets: [{ data: [cat.SAFE, cat.SUSPICIOUS, cat.FRAUDULENT], backgroundColor: [c("--low"), c("--mid"), c("--high")], borderColor: "#fff", borderWidth: 2 }]
    },
    options: { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom" } } }
  });
})();
