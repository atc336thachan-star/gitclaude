(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };

  // Menu mobile
  var drawer = $("#mobile-nav"), toggle = $(".nav-toggle");
  function setDrawer(open) {
    drawer.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    document.body.style.overflow = open ? "hidden" : "";
    if (open) { var f = drawer.querySelector("input,a"); f && f.focus(); } else { toggle.focus(); }
  }
  if (drawer && toggle) {
    toggle.addEventListener("click", function () { setDrawer(true); });
    drawer.querySelectorAll("[data-close]").forEach(function (b) { b.addEventListener("click", function () { setDrawer(false); }); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !drawer.hidden) setDrawer(false); });
  }

  // Bộ lọc trên mobile
  var filters = $("#filters"), scrim = $(".scrim");
  function setFilters(open) {
    if (!filters) return;
    filters.classList.toggle("is-open", open);
    if (scrim) scrim.hidden = !open;
    document.body.style.overflow = open ? "hidden" : "";
  }
  document.querySelectorAll("[data-open-filters]").forEach(function (b) { b.addEventListener("click", function () { setFilters(true); }); });
  document.querySelectorAll("[data-close-filters]").forEach(function (b) { b.addEventListener("click", function () { setFilters(false); }); });

  // Sắp xếp tự gửi
  document.querySelectorAll("[data-autosubmit]").forEach(function (s) {
    s.addEventListener("change", function () { s.form.submit(); });
  });

  // Gallery
  var g = $("[data-gallery]");
  if (g) {
    var main = $("#g-main");
    g.querySelectorAll(".gallery__thumbs button").forEach(function (b) {
      b.addEventListener("click", function () { main.src = b.dataset.src; main.alt = b.dataset.alt; });
    });
  }

  // Chống gửi đúp form
  document.querySelectorAll("form.form").forEach(function (f) {
    f.addEventListener("submit", function () {
      var btn = f.querySelector("button[type=submit]");
      if (btn) { btn.disabled = true; btn.textContent = "Đang gửi…"; }
    });
  });
})();
