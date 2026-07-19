/* app.js — no framework · two independent behaviours:
   1) dropzone UX (preview, drag-drop) — elements exist only on the form page
   2) finding <details> ↔ hotspot sync — delegated on document so it survives HTMX swaps
      (opening a boxed finding lights its region; clicking a region opens its finding) */
(function () {
  "use strict";

  /* ---- 1) dropzone ---- */
  var zone = document.getElementById("dropzone");
  var input = document.getElementById("file-input");
  if (zone && input) {
    var preview = document.getElementById("dz-preview");
    var nameEl = document.getElementById("dz-name");
    var checkingFile = document.getElementById("checking-file");
    var objectUrl = null;

    var showFile = function (file) {
      if (!file) return;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(file);
      preview.src = objectUrl;
      nameEl.textContent = file.name;
      if (checkingFile) checkingFile.textContent = file.name;
      zone.classList.add("has-file");
    };

    input.addEventListener("change", function () {
      showFile(input.files[0]);
    });
    ["dragover", "dragenter"].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault();
        zone.classList.add("dragover");
      });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      zone.addEventListener(ev, function () {
        zone.classList.remove("dragover");
      });
    });
    zone.addEventListener("drop", function (e) {
      e.preventDefault();
      if (e.dataTransfer && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        showFile(input.files[0]);
      }
    });
  }

  /* ---- 2) finding ↔ hotspot ---- */
  var activate = function (fid) {
    var stage = document.querySelector(".ad-stage");
    document.querySelectorAll(".finding.active, .hotspot.active").forEach(function (el) {
      el.classList.remove("active");
    });
    if (stage) stage.classList.remove("has-active");
    if (!fid) return;

    var card = document.querySelector('.finding[data-fid="' + fid + '"]');
    var spot = document.querySelector('.hotspot[data-for="' + fid + '"]');
    if (card) card.classList.add("active");
    if (spot) {
      spot.classList.add("active");
      if (stage) stage.classList.add("has-active");
    }
  };

  // toggle doesn't bubble — listen in the capture phase
  document.addEventListener(
    "toggle",
    function (e) {
      var d = e.target;
      if (!d.classList || !d.classList.contains("finding")) return;
      var fid = d.getAttribute("data-fid");
      if (d.open && fid) {
        activate(fid);
        if (window.matchMedia("(max-width: 1120px)").matches) {
          var spot = document.querySelector('.hotspot[data-for="' + fid + '"]');
          if (spot) spot.scrollIntoView({ behavior: "smooth", block: "center" }); // image sits above on small layouts
        }
      } else if (!d.open && d.classList.contains("active")) {
        activate(null);
      }
    },
    true
  );

  document.addEventListener("click", function (e) {
    var spot = e.target.closest(".hotspot");
    if (!spot) return;
    var fid = spot.getAttribute("data-for");
    var card = document.querySelector('.finding[data-fid="' + fid + '"]');
    if (card) {
      card.open = true; // triggers the toggle handler → activate
      card.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    activate(fid);
  });
})();
