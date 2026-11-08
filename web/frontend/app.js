/* chromadose web — first-pass UI.
 *
 * A dependency-free single-page app over the FastAPI backend (/api/*). State
 * lives in memory only: nothing is written to localStorage or cookies, because
 * exports can carry patient identifiers.
 */
(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  var STEPS = ["calibrate", "solve", "compare", "export", "plan"];

  var state = {
    calFiles: [],       // [{ file, dose }]
    calibration: null,  // parsed calibration JSON from the backend
    filmFile: null,
    measured: null,     // { blob, label }
    reference: null,    // File
    lastMethod: "",
    gammaDone: false,
    planFile: null
  };

  /* ---------- helpers ---------- */

  function fmt(n, digits) {
    if (n === null || n === undefined || !isFinite(n)) { return "–"; }
    return Number(n).toFixed(digits === undefined ? 3 : digits);
  }

  function b64ToBlob(b64, type) {
    var bin = atob(b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) { bytes[i] = bin.charCodeAt(i); }
    return new Blob([bytes], { type: type || "application/octet-stream" });
  }

  function download(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
  }

  function errorText(body, fallback) {
    var d = body && body.detail;
    if (typeof d === "string") { return d; }
    if (Array.isArray(d)) {
      return d.map(function (e) { return e.msg || JSON.stringify(e); }).join("; ");
    }
    return fallback;
  }

  // POST multipart form data; resolves JSON or a Blob. Rejects with a readable Error.
  function api(path, form, wantBlob) {
    return fetch(path, { method: "POST", body: form }).then(function (res) {
      if (res.ok) { return wantBlob ? res.blob() : res.json(); }
      return res.json().catch(function () { return null; }).then(function (body) {
        throw new Error(errorText(body, "Request failed (" + res.status + " " + res.statusText + ")"));
      });
    }, function () {
      throw new Error("Could not reach the server. Is the backend running?");
    });
  }

  function message(id, kind, text) {
    var el = $("#msg-" + id);
    el.className = "msg" + (text ? " " + kind : "");
    el.textContent = text || "";
  }

  // Run `work` with the button disabled and aria-busy (CSS shows a spinner).
  function busy(btn, work) {
    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
    function done() {
      btn.removeAttribute("aria-busy");
      refresh();
    }
    return Promise.resolve().then(work).then(
      function (v) { done(); return v; },
      function (e) { done(); throw e; }
    );
  }

  function stat(key, value, unit) {
    var d = document.createElement("div");
    d.className = "stat";
    var k = document.createElement("span");
    k.className = "k";
    k.textContent = key;
    var v = document.createElement("span");
    v.className = "v";
    v.textContent = value;
    d.appendChild(k);
    d.appendChild(v);
    if (unit) {
      var u = document.createElement("span");
      u.className = "u";
      u.textContent = unit;
      d.appendChild(u);
    }
    return d;
  }

  function dropzone(root, onFiles) {
    var input = $("input", root);
    function take(list) {
      var files = Array.prototype.slice.call(list || []);
      if (files.length) { onFiles(files); }
    }
    input.addEventListener("change", function () { take(input.files); input.value = ""; });
    ["dragenter", "dragover"].forEach(function (t) {
      root.addEventListener(t, function (e) { e.preventDefault(); root.classList.add("over"); });
    });
    ["dragleave", "drop"].forEach(function (t) {
      root.addEventListener(t, function (e) { e.preventDefault(); root.classList.remove("over"); });
    });
    root.addEventListener("drop", function (e) { take(e.dataTransfer && e.dataTransfer.files); });
  }

  function fileLine(id, text) {
    var el = $(id);
    el.textContent = "";
    if (!text) { el.hidden = true; return; }
    var s = document.createElement("strong");
    s.textContent = text;
    el.appendChild(s);
    el.hidden = false;
  }

  /* ---------- navigation ---------- */

  // Render a step. The URL hash is the source of truth, so Back/Forward, deep
  // links and hand-edited URLs all work; an unknown hash falls back to step 1.
  function showStep(name) {
    if (STEPS.indexOf(name) < 0) { name = "calibrate"; }
    STEPS.forEach(function (s) { $("#step-" + s).hidden = s !== name; });
    $$(".steps button").forEach(function (b) {
      if (b.dataset.step === name) { b.setAttribute("aria-current", "step"); }
      else { b.removeAttribute("aria-current"); }
    });
    if (location.hash !== "#" + name) { history.replaceState(null, "", "#" + name); }
    refresh();
  }

  // User-initiated navigation. Setting the hash adds a history entry (so Back
  // works) and fires "hashchange" a tick later; we render now rather than wait,
  // and that later render of the same step is a harmless repeat.
  function navigate(name) {
    if (location.hash.slice(1) !== name) { location.hash = name; }
    showStep(name);
    window.scrollTo(0, 0);
    $("#main").focus();
  }

  function markDone(step, isDone) {
    var b = $('.steps button[data-step="' + step + '"]');
    b.parentElement.classList.toggle("done", !!isDone);
  }

  // Re-evaluate every enabled/visible condition from current state.
  function refresh() {
    $("#btn-calibrate").disabled = state.calFiles.length < 2 || $("#btn-calibrate").hasAttribute("aria-busy");
    $("#solve-needs-cal").hidden = !!state.calibration;
    $("#btn-solve").disabled = !(state.calibration && state.filmFile) || $("#btn-solve").hasAttribute("aria-busy");
    $("#btn-gamma").disabled = !(state.measured && state.reference) || $("#btn-gamma").hasAttribute("aria-busy");
    $("#btn-plan").disabled = !state.planFile || $("#btn-plan").hasAttribute("aria-busy");
    $$("[data-export]").forEach(function (b) {
      b.disabled = !state.measured || b.hasAttribute("aria-busy");
    });

    $$("[data-measured-line]").forEach(function (el) {
      el.textContent = "";
      if (state.measured) {
        var s = document.createElement("strong");
        s.textContent = state.measured.label;
        el.appendChild(s);
      } else {
        el.textContent = el.dataset.empty || el.textContent;
      }
    });
    $("#export-ref-line").textContent = state.reference
      ? "Reference: " + state.reference.name + ". Gamma will be included."
      : "No reference. The report and SR will omit the gamma section. Add one in step 3.";

    markDone("calibrate", !!state.calibration);
    markDone("solve", !!state.measured);
    markDone("compare", state.gammaDone);
  }

  /* ---------- backend status ---------- */

  function loadHealth() {
    var box = $("#status");
    var text = $("#status-text");
    fetch("/api/health").then(function (r) { return r.json(); }).then(function (h) {
      box.className = "status ok";
      text.textContent = "Server ready";
      var ver = document.createElement("span");
      ver.className = "ver";
      ver.textContent = " · chromadose " + h.chromadose_version;
      text.appendChild(ver);
      var sel = $("#method");
      sel.textContent = "";
      (h.methods || ["micke"]).forEach(function (m) {
        var o = document.createElement("option");
        o.value = m;
        o.textContent = m.charAt(0).toUpperCase() + m.slice(1);
        sel.appendChild(o);
      });
    }).catch(function () {
      box.className = "status down";
      text.textContent = "Server unreachable";
      var sel = $("#method");
      if (!sel.options.length) {
        ["micke", "mayer"].forEach(function (m) {
          var o = document.createElement("option");
          o.value = m;
          o.textContent = m.charAt(0).toUpperCase() + m.slice(1);
          sel.appendChild(o);
        });
      }
    });
  }

  /* ---------- 1 · calibrate ---------- */

  function guessDose(name) {
    var m = /(\d+(?:\.\d+)?)\s*gy/i.exec(name);
    return m ? m[1] : "";
  }

  function renderCalTable() {
    var body = $("#cal-table tbody");
    body.textContent = "";
    state.calFiles.forEach(function (row, i) {
      var tr = document.createElement("tr");

      var tdName = document.createElement("td");
      tdName.textContent = row.file.name;

      var tdDose = document.createElement("td");
      var input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.min = "0";
      input.value = row.dose;
      input.setAttribute("aria-label", "Dose in Gy for " + row.file.name);
      input.addEventListener("input", function () { row.dose = input.value; });
      tdDose.appendChild(input);

      var tdRm = document.createElement("td");
      var rm = document.createElement("button");
      rm.type = "button";
      rm.className = "rm";
      rm.textContent = "✕";
      rm.setAttribute("aria-label", "Remove " + row.file.name);
      rm.addEventListener("click", function () {
        state.calFiles.splice(i, 1);
        renderCalTable();
        refresh();
      });
      tdRm.appendChild(rm);

      tr.appendChild(tdName);
      tr.appendChild(tdDose);
      tr.appendChild(tdRm);
      body.appendChild(tr);
    });
    $("#cal-table-wrap").hidden = state.calFiles.length === 0;
  }

  function calibrationChart(cal) {
    var W = 480, H = 270, m = { l: 48, r: 14, t: 12, b: 38 };
    var doses = cal.doses || [];
    var maxD = (Math.max.apply(null, doses) || 1) * 1.1;
    var channels = [["red", "#d9534f", 0], ["green", "#2f9e57", 1], ["blue", "#3b7ddd", 2]];

    function curve(p, d) { return (p.r + p.s * d) / (p.t + d); }

    var ys = [];
    channels.forEach(function (c) {
      var p = cal.fit_params[c[0]];
      for (var i = 0; i <= 60; i++) { ys.push(curve(p, maxD * i / 60)); }
      (cal.pixel_values || []).forEach(function (row) { ys.push(row[c[2]]); });
    });
    var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    var pad = (y1 - y0) * 0.08 || 0.05;
    y0 -= pad; y1 += pad;

    function X(d) { return m.l + (d / maxD) * (W - m.l - m.r); }
    function Y(v) { return H - m.b - ((v - y0) / (y1 - y0)) * (H - m.t - m.b); }

    var svg = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Calibration curves: pixel value against dose for the red, green and blue channels">';
    for (var t = 0; t <= 4; t++) {
      var gy = y0 + (y1 - y0) * t / 4, gx = maxD * t / 4;
      svg += '<line class="grid" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(gy) + '" y2="' + Y(gy) + '"/>';
      svg += '<text x="' + (m.l - 6) + '" y="' + (Y(gy) + 4) + '" text-anchor="end">' + gy.toFixed(2) + "</text>";
      svg += '<text x="' + X(gx) + '" y="' + (H - m.b + 16) + '" text-anchor="middle">' + gx.toFixed(1) + "</text>";
    }
    svg += '<text x="' + (W / 2) + '" y="' + (H - 4) + '" text-anchor="middle">Dose (Gy)</text>';
    svg += '<text transform="translate(12 ' + (H / 2) + ') rotate(-90)" text-anchor="middle">Pixel value</text>';

    channels.forEach(function (c) {
      var p = cal.fit_params[c[0]];
      var path = "";
      for (var i = 0; i <= 80; i++) {
        var d = maxD * i / 80;
        path += (i ? "L" : "M") + X(d).toFixed(1) + " " + Y(curve(p, d)).toFixed(1);
      }
      svg += '<path d="' + path + '" fill="none" stroke="' + c[1] + '" stroke-width="2"/>';
      (cal.pixel_values || []).forEach(function (row, i) {
        svg += '<circle cx="' + X(doses[i]).toFixed(1) + '" cy="' + Y(row[c[2]]).toFixed(1) + '" r="3.5" fill="' + c[1] + '"/>';
      });
    });
    return svg + "</svg>";
  }

  function showCalibration(cal, note) {
    state.calibration = cal;
    var body = $("#cal-fit tbody");
    body.textContent = "";
    ["red", "green", "blue"].forEach(function (ch) {
      var p = cal.fit_params[ch];
      var tr = document.createElement("tr");
      [ch.charAt(0).toUpperCase() + ch.slice(1), fmt(p.r, 4), fmt(p.s, 4), fmt(p.t, 4)].forEach(function (v) {
        var td = document.createElement("td");
        td.textContent = v;
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    $("#cal-chart").innerHTML = calibrationChart(cal);
    $("#cal-result").hidden = false;
    message("calibrate", "ok", note);
    refresh();
  }

  function initCalibrate() {
    dropzone($("#cal-drop"), function (files) {
      files.forEach(function (f) { state.calFiles.push({ file: f, dose: guessDose(f.name) }); });
      // Order by dose (unknown last) so the table reads low → high. Done once on
      // add, not on edit, so rows don't jump while the user is typing.
      state.calFiles.sort(function (a, b) {
        var x = a.dose === "" ? Infinity : Number(a.dose);
        var y = b.dose === "" ? Infinity : Number(b.dose);
        return x - y || (a.file.name < b.file.name ? -1 : 1);
      });
      renderCalTable();
      refresh();
    });

    $("#btn-calibrate").addEventListener("click", function () {
      var btn = this;
      var doses = state.calFiles.map(function (r) { return r.dose; });
      if (doses.some(function (d) { return d === "" || isNaN(Number(d)); })) {
        message("calibrate", "error", "Enter a dose in Gy for every film.");
        return;
      }
      var form = new FormData();
      form.append("doses", doses.join(","));
      state.calFiles.forEach(function (r) { form.append("films", r.file, r.file.name); });
      message("calibrate", "info", "Fitting response curves…");
      busy(btn, function () { return api("/api/calibrate", form); }).then(function (cal) {
        showCalibration(cal, "Calibration built from " + state.calFiles.length + " films.");
      }).catch(function (e) { message("calibrate", "error", e.message); });
    });

    $("#cal-json").addEventListener("change", function () {
      var f = this.files[0];
      this.value = "";
      if (!f) { return; }
      f.text().then(function (txt) {
        var cal = JSON.parse(txt);
        if (!cal.fit_params || !cal.fit_params.red || !cal.fit_params.green || !cal.fit_params.blue) {
          throw new Error("missing fit_params");
        }
        $("#cal-json-name").textContent = f.name;
        showCalibration(cal, "Loaded calibration from " + f.name + ".");
      }).catch(function () {
        message("calibrate", "error", "That file is not a chromadose calibration JSON.");
      });
    });

    $("#btn-cal-download").addEventListener("click", function () {
      download(new Blob([JSON.stringify(state.calibration, null, 2)], { type: "application/json" }), "calibration.json");
    });
  }

  /* ---------- 2 · solve ---------- */

  function initSolve() {
    dropzone($("#film-drop"), function (files) {
      state.filmFile = files[0];
      fileLine("#film-name", state.filmFile.name);
      refresh();
    });

    $("#btn-solve").addEventListener("click", function () {
      var btn = this;
      var method = $("#method").value;
      var form = new FormData();
      form.append("film", state.filmFile, state.filmFile.name);
      form.append("calibration", new Blob([JSON.stringify(state.calibration)], { type: "application/json" }), "calibration.json");
      form.append("method", method);
      message("solve", "info", "Calculating dose…");
      busy(btn, function () { return api("/api/solve", form); }).then(function (res) {
        var stats = $("#solve-stats");
        stats.textContent = "";
        stats.appendChild(stat("Maximum", fmt(res.max_dose_gy), "Gy"));
        stats.appendChild(stat("Mean", fmt(res.mean_dose_gy), "Gy"));
        stats.appendChild(stat("Mean uncertainty", fmt(res.mean_uncertainty_gy), "Gy"));
        stats.appendChild(stat("Size", res.shape[1] + " × " + res.shape[0], "px"));
        $("#solve-img").src = res.preview_png;
        $("#solve-result").hidden = false;
        state.lastMethod = method;
        $("#x-method").value = method;
        state.measured = {
          blob: b64ToBlob(res.dose_npy_b64),
          label: "Dose map from " + state.filmFile.name + " (" + method + ")"
        };
        refresh();
        message("solve", "ok", "Dose map ready.");
      }).catch(function (e) { message("solve", "error", e.message); });
    });

    $("#btn-dose-download").addEventListener("click", function () {
      if (state.measured) { download(state.measured.blob, "dose.npy"); }
    });
  }

  /* ---------- 3 · compare ---------- */

  function initCompare() {
    dropzone($("#ref-drop"), function (files) {
      state.reference = files[0];
      fileLine("#ref-name", state.reference.name);
      refresh();
    });

    $$("[data-measured-input]").forEach(function (input) {
      input.addEventListener("change", function () {
        var f = input.files[0];
        input.value = "";
        if (!f) { return; }
        state.measured = { blob: f, label: "Uploaded " + f.name };
        $("#solve-result").hidden = true;
        refresh();
      });
    });

    $("#btn-gamma").addEventListener("click", function () {
      var btn = this;
      var form = new FormData();
      form.append("measured", state.measured.blob, "measured.npy");
      form.append("reference", state.reference, state.reference.name);
      form.append("criteria", numberAt("dose-crit") + "/" + numberAt("dta-crit"));
      form.append("threshold", numberAt("threshold"));
      form.append("pixel_size_mm", numberAt("pixel"));
      message("compare", "info", "Running gamma analysis…");
      busy(btn, function () { return api("/api/gamma", form); }).then(function (res) {
        var target = Number($("#target-pass").value);
        var box = $("#gamma-pass");
        box.className = "passrate " + (res.pass_rate_pct >= target ? "pass" : res.pass_rate_pct >= target - 5 ? "near" : "fail");
        $("#gamma-pct").textContent = fmt(res.pass_rate_pct, 1) + "%";
        $("#gamma-meta").textContent = "pass rate · " + res.criteria;
        var stats = $("#gamma-stats");
        stats.textContent = "";
        stats.appendChild(stat("Points evaluated", String(res.points_evaluated)));
        stats.appendChild(stat("Points passed", String(res.points_passed)));
        $("#gamma-img").src = res.preview_png;
        $("#gamma-result").hidden = false;
        state.gammaDone = true;
        refresh();
        message("compare", "ok", "Gamma analysis complete.");
      }).catch(function (e) { message("compare", "error", e.message); });
    });
  }

  function numberAt(name) {
    return $('input[data-sync="' + name + '"]').value;
  }

  // Criteria and pixel size appear in both Compare and Export; keep them equal.
  function initSync() {
    $$("input[data-sync]").forEach(function (input) {
      input.addEventListener("input", function () {
        $$('input[data-sync="' + input.dataset.sync + '"]').forEach(function (o) {
          if (o !== input) { o.value = input.value; }
        });
      });
    });
  }

  /* ---------- 4 · export ---------- */

  function exportForm(kind) {
    var form = new FormData();
    var name = $("#x-patient-name").value, pid = $("#x-patient-id").value, plan = $("#x-plan").value;
    var measured = state.measured.blob;

    if (kind === "rtdose") {
      form.append("dose", measured, "dose.npy");
      form.append("pixel_size_mm", numberAt("pixel"));
      form.append("patient_name", name);
      form.append("patient_id", pid);
      form.append("plan_label", plan);
    } else if (kind === "sr") {
      form.append("measured", measured, "measured.npy");
      if (state.reference) { form.append("reference", state.reference, state.reference.name); }
      form.append("criteria", numberAt("dose-crit") + "/" + numberAt("dta-crit"));
      form.append("threshold", numberAt("threshold"));
      form.append("pixel_size_mm", numberAt("pixel"));
      form.append("method", $("#x-method").value);
      form.append("film_type", $("#x-film").value);
      form.append("patient_name", name);
      form.append("patient_id", pid);
      form.append("plan_label", plan);
    } else {
      form.append("measured", measured, "measured.npy");
      if (state.reference) { form.append("reference", state.reference, state.reference.name); }
      form.append("title", $("#x-title").value);
      form.append("patient_id", pid);
      form.append("plan_name", plan);
    }
    return form;
  }

  var EXPORTS = {
    rtdose: { path: "/api/export/rtdose", file: "dose.dcm", label: "DICOM RT Dose" },
    sr: { path: "/api/export/sr", file: "qa_sr.dcm", label: "DICOM Structured Report" },
    report: { path: "/api/report", file: "report.pdf", label: "PDF report" }
  };

  function initExport() {
    $$("[data-export]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var spec = EXPORTS[btn.dataset.export];
        message("export", "info", "Preparing " + spec.label + "…");
        busy(btn, function () {
          return api(spec.path, exportForm(btn.dataset.export), true);
        }).then(function (blob) {
          download(blob, spec.file);
          message("export", "ok", spec.label + " downloaded as " + spec.file + ".");
        }).catch(function (e) { message("export", "error", e.message); });
      });
    });
  }

  /* ---------- tool · RT plan geometry ---------- */

  function initPlan() {
    dropzone($("#plan-drop"), function (files) {
      state.planFile = files[0];
      fileLine("#plan-name", state.planFile.name);
      refresh();
    });

    $("#btn-plan").addEventListener("click", function () {
      var btn = this;
      var form = new FormData();
      form.append("rtplan", state.planFile, state.planFile.name);
      form.append("include_setup", $("#plan-setup").checked ? "true" : "false");
      message("plan", "info", "Reading plan…");
      busy(btn, function () { return api("/api/plan-geometry", form); }).then(function (res) {
        var body = $("#plan-table tbody");
        body.textContent = "";
        res.beams.forEach(function (b) {
          var tr = document.createElement("tr");
          [
            b.beam_number === null ? "–" : String(b.beam_number),
            b.beam_name || "–",
            fmt(b.gantry_angle, 1),
            fmt(b.collimator_angle, 1),
            fmt(b.couch_angle, 1),
            b.beam_energy_mv === null ? "–" : b.beam_energy_mv + " MV"
          ].forEach(function (v) {
            var td = document.createElement("td");
            td.textContent = v;
            tr.appendChild(td);
          });
          body.appendChild(tr);
        });
        $("#plan-result").hidden = false;
        message("plan", res.beams.length ? "ok" : "info",
          res.beams.length ? res.beams.length + " beam(s) found." : "No treatment beams in this plan.");
      }).catch(function (e) { message("plan", "error", e.message); });
    });
  }

  /* ---------- boot ---------- */

  function init() {
    $$("[data-measured-line]").forEach(function (el) { el.dataset.empty = el.textContent; });

    $$(".steps button").forEach(function (b) {
      b.addEventListener("click", function () { navigate(b.dataset.step); });
    });
    $$("[data-goto]").forEach(function (b) {
      b.addEventListener("click", function () { navigate(b.dataset.goto); });
    });
    window.addEventListener("hashchange", function () { showStep(location.hash.slice(1)); });

    initCalibrate();
    initSolve();
    initCompare();
    initSync();
    initExport();
    initPlan();
    loadHealth();

    showStep(location.hash.slice(1));
  }

  init();
})();
