/* Общий скрипт: блокирует кнопку после отправки формы (защита от двойного клика). Без inline-скриптов — работает под CSP. */
document.addEventListener("submit", function (e) {
  var btn = e.target.querySelector("button[data-busy]");
  if (btn && !e.defaultPrevented) {
    btn.setAttribute("data-label", btn.textContent);
    btn.disabled = true;
    btn.textContent = btn.getAttribute("data-busy");
  }
});
window.addEventListener("pageshow", function () {   // возврат кнопкой «Назад»
  document.querySelectorAll("button[data-busy][data-label]").forEach(function (b) {
    b.disabled = false;
    b.textContent = b.getAttribute("data-label");
  });
});
