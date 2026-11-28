#!/usr/bin/env node
// Optional browser QA. Uses an existing Playwright installation, never installs one.
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const args = process.argv.slice(2);
function option(name, fallback) {
  const index = args.indexOf(name);
  return index < 0 ? fallback : args[index + 1];
}
if (args.includes("--help") || !args.length) {
  console.log("Usage: node render.mjs DECK_DIRECTORY --output REVIEW_DIRECTORY [--playwright MODULE_OR_DIRECTORY] [--browser EXECUTABLE]");
  process.exit(args.includes("--help") ? 0 : 1);
}
const root = path.resolve(args[0]);
const outputArg = option("--output");
if (!outputArg) throw new Error("--output is required. Keep review files outside the deck.");
const output = path.resolve(outputArg);
if (output === root || output.startsWith(root + path.sep)) throw new Error("Put review output outside the presentation directory.");
const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require(option("--playwright", "playwright")));
} catch {
  throw new Error("Playwright is unavailable. Pass --playwright pointing to an existing installation. Static checks remain available with deck.py check.");
}
const launch = { headless: true };
if (option("--browser")) launch.executablePath = path.resolve(option("--browser"));
let browser;
try {
  browser = await chromium.launch(launch);
} catch (error) {
  console.error("Browser failed to start. Visual and PDF checks were not performed.");
  console.error(error.message);
  process.exit(2);
}
try {
  await fs.mkdir(output, { recursive: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 948 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  // The complete deck should work from disk. Block accidental CDN dependencies.
  await page.route(/^https?:/, route => {
    errors.push(`Unexpected network dependency: ${route.request().url()}`);
    return route.abort();
  });
  await page.goto(pathToFileURL(path.join(root, "index.html")).href);
  await page.waitForFunction(() => window.presentation);
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(img => img.decode().catch(() => {})));
  });
  const reports = await page.evaluate(() => window.presentation.layout());
  const broken = await page.evaluate(() => [...document.images].filter(img => !img.complete || !img.naturalWidth).map(img => img.getAttribute("src")));
  errors.push(...broken.map(src => `Broken image: ${src}`));
  const count = await page.evaluate(() => window.presentation.count);
  for (let index = 0; index < count; index++) {
    await page.evaluate(index => window.presentation.go(index), index);
    await page.locator(".slide.active").screenshot({ path: path.join(output, `slide-${String(index + 1).padStart(2, "0")}.png`) });
  }
  const assert = (result, message) => { if (!result) errors.push(message); };
  await page.keyboard.press("Home");
  assert(await page.locator("#counter").textContent() === `1 / ${count}`, "Home navigation failed");
  if (count > 1) {
    await page.keyboard.press("ArrowRight");
    assert(await page.locator("#counter").textContent() === `2 / ${count}`, "Arrow navigation failed");
  }
  await page.keyboard.press("End");
  assert(await page.locator("#counter").textContent() === `${count} / ${count}`, "End navigation failed");
  await page.keyboard.press("o");
  await page.locator("#overview button").first().click();
  assert(await page.locator("#counter").textContent() === `1 / ${count}`, "Overview selection failed");
  await page.keyboard.press("n");
  assert(await page.locator(".slide.active .notes").isVisible(), "Presenter notes failed");
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(output, "mobile.png") });
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  assert(!mobileOverflow, "Mobile toolbar overflows the viewport");
  await page.setViewportSize({ width: 1600, height: 948 });
  await page.pdf({ path: path.join(output, "presentation.pdf"), preferCSSPageSize: true, printBackground: true });
  const result = { slides: count, errors, layouts: reports };
  await fs.writeFile(path.join(output, "report.json"), JSON.stringify(result, null, 2) + "\n");
  console.log(JSON.stringify(result, null, 2));
  if (errors.length || reports.some(report => report.warnings.length)) process.exitCode = 1;
} finally {
  await browser.close();
}
