// Confirmation before destructive actions, and select-all for review tables.
document.addEventListener("submit", function (event) {
  var message = event.target.getAttribute("data-confirm");
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});
document.addEventListener("change", function (event) {
  if (event.target.id === "select-all") {
    document.querySelectorAll("input.row-check").forEach(function (box) {
      if (!box.disabled) { box.checked = event.target.checked; }
    });
  }
});
