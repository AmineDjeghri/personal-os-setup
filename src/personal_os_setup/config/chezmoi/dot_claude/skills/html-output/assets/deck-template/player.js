/* Canonical player. Refresh generated copies with deck.py sync. */
(() => {
  "use strict";

  const deck = document.getElementById("deck");
  const slides = [...deck.querySelectorAll(":scope > .slide")];
  const viewport = document.getElementById("viewport");
  const overview = document.getElementById("overview");
  const help = document.getElementById("help");
  const button = id => document.getElementById(id);
  const minimumScale = Math.max(0.85, Math.min(1, Number(deck.dataset.minScale) || 0.85));
  let current = 0;
  let helpTrigger;
  let resizeFrame;
  let reports = [];

  function element(tag, text, className) {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (className) result.className = className;
    return result;
  }

  function title(slide) {
    const heading = slide.querySelector("h1");
    // textContent drops the whitespace at <br>, joining words in navigation.
    const copy = heading.cloneNode(true);
    copy.querySelectorAll("br").forEach(br => br.replaceWith(" "));
    return copy.textContent.replace(/\s+/g, " ").trim();
  }

  function addChrome(slide, index) {
    const brand = element("header", undefined, "brand");
    if (deck.dataset.logo) {
      const logo = element("img");
      logo.src = deck.dataset.logo;
      logo.alt = deck.dataset.logoAlt || "Team logo";
      brand.append(logo);
    } else {
      brand.classList.add("no-logo");
    }
    brand.append(element("span", deck.dataset.team || ""));
    const footer = element("footer");
    footer.append(element("span", deck.dataset.footer || document.title));
    const page = element("span", String(index + 1).padStart(2, "0"), "page");
    page.append(element("span", `/ ${slides.length}`));
    footer.append(page);
    slide.prepend(brand);
    slide.append(footer);
    if (!slide.id) slide.id = `slide-${index + 1}`;
    slide.setAttribute("aria-label", `Slide ${index + 1}: ${title(slide)}`);
    const entry = element("button");
    entry.type = "button";
    entry.append(element("span", `SLIDE ${String(index + 1).padStart(2, "0")}`));
    entry.append(document.createTextNode(title(slide)));
    entry.onclick = () => { go(index); setOverview(false); button("overview-button").focus(); };
    overview.append(entry);
  }

  function measureSlide(slide, index) {
    const previousDisplay = slide.style.display;
    const previousVisibility = slide.style.visibility;
    slide.style.display = "block";
    slide.style.visibility = "hidden";
    const content = slide.querySelector(".content");
    const main = slide.querySelector("main");
    const footer = slide.querySelector("footer");
    content.style.transform = "none";
    const available = footer.offsetTop - main.offsetTop - content.offsetTop - 22;
    const naturalHeight = content.scrollHeight;
    const required = naturalHeight > 0 ? Math.min(1, available / naturalHeight) : 1;
    // A cover has positioned artwork and is checked without scaling its composition.
    const scale = slide.classList.contains("cover") ? 1 : Math.max(minimumScale, required);
    if (!slide.classList.contains("cover")) {
      content.style.transform = `translateX(${(1440 - 1440 * scale) / 2}px) scale(${scale})`;
    }
    slide.dataset.contentScale = String(scale);
    const warnings = [];
    if (!slide.classList.contains("cover") && required < minimumScale - 0.005) {
      warnings.push("Content needs more space. Shorten it or split this slide.");
    }
    const frame = slide.getBoundingClientRect();
    const footerTop = footer.getBoundingClientRect().top;
    const unit = frame.width / 1600 || 1;
    const region = content.getBoundingClientRect();
    for (const child of slide.querySelectorAll("main h1, main .subtitle, .content p, .content pre, .content .node, .content table")) {
      const box = child.getBoundingClientRect();
      if (!box.width || !box.height) continue;
      if (box.bottom > footerTop - 12 * unit || box.left < frame.left + 65 * unit || box.right > frame.right - 65 * unit) {
        warnings.push(`Outside content area: ${child.textContent.trim().slice(0, 70)}`);
      }
    }
    for (const text of content.querySelectorAll("p, pre, td, li, .node strong, .node span")) {
      const pixels = parseFloat(getComputedStyle(text).fontSize) * scale;
      if (pixels < 17 - 0.01) {
        warnings.push(`Text below 17px on the slide canvas: ${text.textContent.trim().slice(0, 50)}`);
      }
    }
    if (region.width > frame.width) warnings.push("Content is wider than the slide.");
    slide.dataset.layoutWarning = warnings.length ? "true" : "false";
    slide.style.display = previousDisplay;
    slide.style.visibility = previousVisibility;
    return { slide: index + 1, title: title(slide), scale, requiredScale: required, warnings: [...new Set(warnings)] };
  }

  function layout() {
    // Measure once without the viewport transform, so screen size cannot change fit.
    deck.style.transform = "none";
    reports = slides.map(measureSlide);
    deck.style.transform = `scale(${Math.min(viewport.clientWidth / 1600, viewport.clientHeight / 900)})`;
    const warnings = reports.filter(report => report.warnings.length);
    const status = button("layout-status");
    if (status) {
      status.hidden = warnings.length === 0;
      status.textContent = `${warnings.length} crowded slide${warnings.length === 1 ? "" : "s"}`;
      status.title = warnings.map(report => `${report.slide}: ${report.warnings.join(" ")}`).join("\n");
    }
    return reports;
  }

  function go(index, updateHash = true) {
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides.forEach((slide, i) => {
      slide.classList.toggle("active", i === current);
      slide.setAttribute("aria-hidden", String(i !== current));
      slide.inert = i !== current;
    });
    [...overview.children].forEach((entry, i) => {
      entry.classList.toggle("current", i === current);
      entry.setAttribute("aria-current", String(i === current));
    });
    button("counter").textContent = `${current + 1} / ${slides.length}`;
    button("announcement").textContent = `Slide ${current + 1} of ${slides.length}: ${title(slides[current])}`;
    button("progress").style.width = `${(current + 1) / slides.length * 100}%`;
    button("previous").disabled = current === 0;
    button("next").disabled = current === slides.length - 1;
    if (updateHash) history.replaceState(null, "", `#${slides[current].id}`);
  }

  function readHash() {
    const id = location.hash.slice(1);
    const index = slides.findIndex(slide => slide.id === id);
    go(index < 0 ? 0 : index, false);
  }

  function setOverview(open) {
    document.body.classList.toggle("overview-open", open);
    deck.inert = open;
    button("overview-button").setAttribute("aria-expanded", String(open));
    if (open) overview.children[current].focus();
  }

  function setNotes(open) {
    document.body.classList.toggle("notes-visible", open);
    button("notes-button").setAttribute("aria-pressed", String(open));
  }

  function closeHelp() {
    help.classList.remove("open");
    if (helpTrigger) helpTrigger.focus();
  }

  async function fullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      button("announcement").textContent = "Fullscreen unavailable. Use your browser fullscreen command.";
    }
  }

  if (!slides.length) throw new Error("The deck needs at least one slide.");
  slides.forEach(addChrome);
  const hint = document.querySelector("#toolbar .hint");
  if (hint) hint.textContent = document.title;
  button("previous").onclick = () => go(current - 1);
  button("next").onclick = () => go(current + 1);
  button("overview-button").onclick = () => setOverview(!document.body.classList.contains("overview-open"));
  button("notes-button").onclick = () => setNotes(!document.body.classList.contains("notes-visible"));
  button("fullscreen").onclick = fullscreen;
  button("print").onclick = () => window.print();
  button("help-button").onclick = () => {
    helpTrigger = document.activeElement;
    help.classList.add("open");
    button("close-help").focus();
  };
  button("close-help").onclick = closeHelp;
  help.addEventListener("click", event => { if (event.target === help) closeHelp(); });
  if (button("layout-status")) button("layout-status").onclick = () => {
    const next = reports.findIndex(report => report.warnings.length);
    if (next >= 0) go(next);
    console.table(reports.filter(report => report.warnings.length));
  };

  window.addEventListener("keydown", event => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.target.isContentEditable || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName)) return;
    if (help.classList.contains("open")) {
      if (event.key === "Escape") closeHelp();
      if (event.key === "Tab") { event.preventDefault(); button("close-help").focus(); }
      return;
    }
    if (event.key === "Escape") {
      if (document.body.classList.contains("overview-open")) button("overview-button").focus();
      setOverview(false); setNotes(false); return;
    }
    if (document.body.classList.contains("overview-open")) {
      if (event.key.toLowerCase() === "o") { setOverview(false); button("overview-button").focus(); }
      return;
    }
    if (event.target.closest("button, a") && ["Enter", " "].includes(event.key)) return;
    if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(event.key)) { event.preventDefault(); go(current + 1); }
    else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(event.key)) { event.preventDefault(); go(current - 1); }
    else if (event.key === "Home") { event.preventDefault(); go(0); }
    else if (event.key === "End") { event.preventDefault(); go(slides.length - 1); }
    else if (event.key.toLowerCase() === "o") setOverview(true);
    else if (event.key.toLowerCase() === "n") setNotes(!document.body.classList.contains("notes-visible"));
    else if (event.key.toLowerCase() === "f") fullscreen();
    else if (event.key.toLowerCase() === "p") window.print();
    else if (event.key === "?") button("help-button").click();
  });

  let touch;
  viewport.addEventListener("touchstart", event => {
    const point = event.changedTouches[0];
    touch = { x: point.clientX, y: point.clientY, target: event.target };
  }, { passive: true });
  viewport.addEventListener("touchend", event => {
    if (!touch || touch.target.closest("a, button, .notes, pre") || document.body.classList.contains("overview-open")) return;
    const point = event.changedTouches[0];
    const dx = point.clientX - touch.x;
    const dy = point.clientY - touch.y;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) go(current + (dx < 0 ? 1 : -1));
    touch = undefined;
  }, { passive: true });
  window.addEventListener("resize", () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(layout);
  });
  window.addEventListener("hashchange", readHash);
  window.addEventListener("beforeprint", () => { layout(); document.body.classList.add("printing"); });
  window.addEventListener("afterprint", () => { document.body.classList.remove("printing"); layout(); });
  window.presentation = Object.freeze({ go, layout, inspect: () => reports, get current() { return current; }, get count() { return slides.length; } });
  readHash();
  layout();
  if (document.fonts) document.fonts.ready.then(layout);
  window.addEventListener("load", layout, { once: true });
})();
