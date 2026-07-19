/* app.js — no framework · two independent behaviours:
   1) dropzone UX (preview, drag-drop) — elements exist only on the form page
   2) finding ↔ hotspot sync — delegated on document so it survives HTMX swaps */
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
  var activate = function (fid, scrollToCard) {
    var stage = document.querySelector(".ad-stage");
    var wasActive = document.querySelector('.finding.active[data-fid="' + fid + '"]');
    document.querySelectorAll(".finding.active, .hotspot.active").forEach(function (el) {
      el.classList.remove("active");
    });
    if (stage) stage.classList.remove("has-active");
    if (wasActive) return; // second click on the same finding = toggle off

    var card = document.querySelector('.finding[data-fid="' + fid + '"]');
    var spot = document.querySelector('.hotspot[data-for="' + fid + '"]');
    if (card) card.classList.add("active");
    if (spot) {
      spot.classList.add("active");
      if (stage) stage.classList.add("has-active");
    }
    if (scrollToCard && card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
    } else if (spot && window.matchMedia("(max-width: 1080px)").matches) {
      spot.scrollIntoView({ behavior: "smooth", block: "center" }); // image is off-screen on small layouts
    }
  };

  document.addEventListener("click", function (e) {
    var spot = e.target.closest(".hotspot");
    if (spot) {
      activate(spot.getAttribute("data-for"), true);
      return;
    }
    var card = e.target.closest(".finding.has-box");
    if (card) activate(card.getAttribute("data-fid"), false);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" && e.key !== " ") return;
    var card = e.target.closest ? e.target.closest(".finding.has-box") : null;
    if (card) {
      e.preventDefault();
      activate(card.getAttribute("data-fid"), false);
    }
  });
})();
