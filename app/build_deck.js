const pptxgen = require("pptxgenjs");

const NAVY = "1E2761";
const ICE = "CADCFC";
const TERRA = "B5541C";
const WHITE = "FFFFFF";
const OFFWHITE = "F7F7F5";
const TEXT = "1F1F1D";
const MUTED = "6B6B66";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5in
const W = 13.33, H = 7.5;

function motifCircles(slide, opts = {}) {
  const color = opts.color || TERRA;
  slide.addShape("ellipse", { x: W - 1.6, y: -1.0, w: 3.2, h: 3.2, fill: { color, transparency: 88 }, line: { type: "none" } });
  slide.addShape("ellipse", { x: -1.2, y: H - 1.8, w: 2.6, h: 2.6, fill: { color, transparency: 90 }, line: { type: "none" } });
}

function statCard(slide, x, y, w, h, value, label, opts = {}) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.12, fill: { color: opts.cardFill || WHITE }, line: { color: "E3E2DE", width: 1 },
    shadow: { type: "outer", color: "000000", opacity: 0.08, blur: 6, offset: 2, angle: 90 } });
  slide.addText(value, { x: x + 0.25, y: y + 0.15, w: w - 0.5, h: h * 0.55, isTextBox: true, margin: 0,
    fontFace: "Cambria", fontSize: opts.valueSize || 30, bold: true, color: opts.valueColor || TERRA, align: "left", valign: "bottom" });
  slide.addText(label, { x: x + 0.25, y: y + h * 0.6, w: w - 0.5, h: h * 0.38, isTextBox: true, margin: 0,
    fontFace: "Calibri", fontSize: 12.5, color: MUTED, align: "left", valign: "top" });
}

function header(slide, kicker, title) {
  slide.addText(kicker.toUpperCase(), { x: 0.6, y: 0.4, w: 12, h: 0.4, isTextBox: true, margin: 0,
    fontFace: "Calibri", fontSize: 13, bold: true, color: TERRA, charSpacing: 1.5 });
  slide.addText(title, { x: 0.6, y: 0.78, w: 12.1, h: 1.0, isTextBox: true, margin: 0,
    fontFace: "Cambria", fontSize: 28, bold: true, color: TEXT, align: "left" });
}

function pageNum(slide, n) {
  slide.addText(String(n).padStart(2, "0"), { x: W - 0.9, y: H - 0.55, w: 0.6, h: 0.35, isTextBox: true, margin: 0,
    fontFace: "Calibri", fontSize: 11, color: MUTED, align: "right" });
}

// ---------- Slide 1: Title ----------
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  motifCircles(s, { color: TERRA });
  s.addShape("ellipse", { x: 0.8, y: 1.3, w: 0.9, h: 0.9, fill: { color: TERRA }, line: { type: "none" } });
  s.addText("AD", { x: 0.8, y: 1.3, w: 0.9, h: 0.9, isTextBox: true, margin: 0, align: "center", valign: "middle",
    fontFace: "Cambria", fontSize: 22, bold: true, color: WHITE });
  s.addText("SAME-DAY NUMBERS YOU CAN\nACTUALLY TRUST", { x: 0.6, y: 2.6, w: 11.8, h: 1.9, isTextBox: true, margin: 0,
    fontFace: "Cambria", fontSize: 42, bold: true, color: WHITE, align: "left", lineSpacing: 44 });
  s.addText("A dbt-core + DuckDB pipeline built to survive a deliberately hostile ad-platform upstream — and prove it, not just claim it.",
    { x: 0.62, y: 4.55, w: 9.5, h: 0.8, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 17, color: ICE, align: "left" });
  s.addText("484 creatives  ·  25 campaigns  ·  8 injected defect types  ·  10 dbt tests  ·  0 advertising claims",
    { x: 0.62, y: 6.5, w: 11, h: 0.5, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 13, color: "9BAAD8", align: "left" });
}

// ---------- Slide 2: The problem ----------
{
  const s = pres.addSlide();
  s.background = { color: OFFWHITE };
  header(s, "The Problem", "Same-day reporting is a myth without reliability engineering");
  s.addText(
    "Media buyers usually find out which creatives are winning a week after the numbers mattered — platform reporting takes that long to stabilise. Promising a same-day number is easy. Proving it holds up when the upstream data misbehaves is the actual engineering problem, and it's the one this project answers.",
    { x: 0.6, y: 2.0, w: 6.6, h: 3.6, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 15, color: TEXT, align: "left", lineSpacing: 22 }
  );
  s.addText("Real ad-platform data, simulated honestly: 96 daily drop files, deliberately corrupted on delivery.",
    { x: 0.6, y: 5.9, w: 6.6, h: 0.8, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 12.5, italic: true, color: MUTED });

  statCard(s, 7.7, 2.0, 5.0, 1.15, "2,656", "late-arriving rows, delivered 1–3 days after their event date");
  statCard(s, 7.7, 3.35, 5.0, 1.15, "1,260", "restated rows — an initial wrong value, corrected later");
  statCard(s, 7.7, 4.7, 5.0, 1.15, "1 day", "the platform never delivers at all — permanently, not late");
  pageNum(s, 2);
}

// ---------- Slide 3: The approach ----------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "The Approach", "A hostile-input generator, not a happy-path demo");
  s.addText(
    "A generator produces the correct ground truth first, then corrupts it on delivery — 8 named defect types, every instance logged to a manifest so the pipeline's handling of each one can be checked against a known answer.",
    { x: 0.6, y: 2.0, w: 4.6, h: 3.2, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 14.5, color: TEXT, lineSpacing: 21 }
  );
  s.addText("4,492 individually logged defect events across 25,892 ground-truth rows.",
    { x: 0.6, y: 6.5, w: 6.0, h: 0.6, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 12, italic: true, color: MUTED });

  const chartData = [{
    name: "Row-level defects",
    labels: ["Late arrival", "Restatement", "Null value", "Duplicate (near)", "Duplicate (exact)", "Clicks > impressions"],
    values: [2656, 1260, 276, 111, 109, 78],
  }];
  s.addChart(pres.ChartType.bar, chartData, {
    x: 5.5, y: 1.9, w: 7.2, h: 5.0,
    barDir: "bar",
    showTitle: true, title: "Defects injected (96 drop files)", titleFontSize: 13, titleColor: TEXT, titleFontFace: "Calibri",
    showLegend: false,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: TEXT,
    chartColors: [TERRA],
    catAxisLabelFontSize: 11, catAxisLabelColor: TEXT,
    valAxisHidden: true,
    valGridLine: { style: "none" },
    catGridLine: { style: "none" },
  });
  pageNum(s, 3);
}

// ---------- Slide 4: self-heal vs not ----------
{
  const s = pres.addSlide();
  s.background = { color: OFFWHITE };
  header(s, "The Core Distinction", "Not every defect is supposed to fix itself");

  s.addShape("roundRect", { x: 0.6, y: 2.05, w: 5.9, h: 4.6, rectRadius: 0.12, fill: { color: WHITE }, line: { color: "CFE8D4", width: 1.5 } });
  s.addText("SELF-HEALS WITHIN 7 DAYS", { x: 0.95, y: 2.35, w: 5.2, h: 0.4, isTextBox: true, margin: 0,
    fontFace: "Calibri", fontSize: 13, bold: true, color: "2F6B3F", charSpacing: 1 });
  s.addText(
    "The platform eventually delivers a correct, unambiguous version — dedup and a 7-day lookback window converge on it automatically.",
    { x: 0.95, y: 2.8, w: 5.2, h: 0.9, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 13, color: TEXT, lineSpacing: 18 });
  ["Late-arriving rows", "Restated numbers", "Cross-file duplicates"].forEach((t, i) => {
    s.addShape("ellipse", { x: 0.95, y: 3.95 + i * 0.85, w: 0.16, h: 0.16, fill: { color: "2F6B3F" }, line: { type: "none" } });
    s.addText(t, { x: 1.25, y: 3.83 + i * 0.85, w: 5.0, h: 0.4, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 15, bold: true, color: TEXT });
  });

  s.addShape("roundRect", { x: 6.83, y: 2.05, w: 5.9, h: 4.6, rectRadius: 0.12, fill: { color: WHITE }, line: { color: "EBD3C4", width: 1.5 } });
  s.addText("STAYS VISIBLE ON PURPOSE", { x: 7.18, y: 2.35, w: 5.2, h: 0.4, isTextBox: true, margin: 0,
    fontFace: "Calibri", fontSize: 13, bold: true, color: TERRA, charSpacing: 1 });
  s.addText(
    "The generator never issues a correction for these — a pipeline that quietly matched them to ground truth would be inventing numbers.",
    { x: 7.18, y: 2.8, w: 5.2, h: 0.9, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 13, color: TEXT, lineSpacing: 18 });
  ["Nulled fields", "Clicks > impressions bug", "Same-file near-duplicates"].forEach((t, i) => {
    s.addShape("ellipse", { x: 7.18, y: 3.95 + i * 0.85, w: 0.16, h: 0.16, fill: { color: TERRA }, line: { type: "none" } });
    s.addText(t, { x: 7.48, y: 3.83 + i * 0.85, w: 5.0, h: 0.4, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 15, bold: true, color: TEXT });
  });
  pageNum(s, 4);
}

// ---------- Slide 5: missing day ----------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "A Real Finding", "A lost day costs more than the lost day");
  s.addText(
    "One day the platform never delivers at all — not late, permanently absent. The pipeline correctly shows nothing for it. What's less obvious: the damage reaches backward too.",
    { x: 0.6, y: 2.0, w: 11.8, h: 1.0, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 15, color: TEXT, lineSpacing: 21 }
  );

  const total = 281, missing = 253, swallowed = 28;
  const barY = 3.6, barH = 0.9, barX = 0.6, barW = 11.8;
  const missW = barW * (missing / total), swalW = barW * (swallowed / total);
  s.addShape("rect", { x: barX, y: barY, w: missW, h: barH, fill: { color: TERRA }, line: { type: "none" } });
  s.addShape("rect", { x: barX + missW, y: barY, w: swalW, h: barH, fill: { color: "E8B99A" }, line: { type: "none" } });
  s.addText("253", { x: barX, y: barY, w: missW, h: barH, isTextBox: true, margin: 0, align: "center", valign: "middle",
    fontFace: "Cambria", fontSize: 20, bold: true, color: WHITE });
  s.addText("+28", { x: barX + missW, y: barY, w: swalW, h: barH, isTextBox: true, margin: 0, align: "center", valign: "middle",
    fontFace: "Cambria", fontSize: 16, bold: true, color: TEXT });

  s.addText("Rows lost on the missing day itself", { x: barX, y: barY + barH + 0.15, w: 6, h: 0.4, isTextBox: true, margin: 0,
    fontFace: "Calibri", fontSize: 12.5, color: MUTED });
  s.addText("Late arrivals from the 3 days before it, scheduled to land that day",
    { x: barX + barW - 6.5, y: barY + barH + 0.15, w: 6.5, h: 0.4, isTextBox: true, margin: 0,
      fontFace: "Calibri", fontSize: 12.5, color: MUTED, align: "right" });

  s.addText("A platform outage doesn't just cost the day it happens on — it costs whatever was queued to arrive late on that day, from the days before it.",
    { x: 0.6, y: 5.6, w: 11.8, h: 1.0, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 16, italic: true, color: TERRA, lineSpacing: 22 });
  pageNum(s, 5);
}

// ---------- Slide 6: safety net ----------
{
  const s = pres.addSlide();
  s.background = { color: OFFWHITE };
  header(s, "The Safety Net", "10 dbt tests, one designed to warn every run");

  const rows = [
    ["Uniqueness & not-null", "On every key column, in staging and marts"],
    ["Referential integrity", "Every fact row resolves to a real dimension row"],
    ["assert_clicks_lte_impressions", "severity=warn on purpose — expected to find ~76–78 rows every run, since that bug is never corrected upstream"],
    ["assert_reconciliation_within_lookback", "Compares the pipeline's own output against the generator's ground truth, scoped to the 7-day lookback window"],
  ];
  let y = 2.1;
  rows.forEach(([t, d], i) => {
    s.addShape("roundRect", { x: 0.6, y, w: 12.1, h: 1.0, rectRadius: 0.1, fill: { color: WHITE }, line: { color: "E3E2DE", width: 1 } });
    s.addShape("ellipse", { x: 0.9, y: y + 0.3, w: 0.4, h: 0.4, fill: { color: TERRA }, line: { type: "none" } });
    s.addText(String(i + 1), { x: 0.9, y: y + 0.3, w: 0.4, h: 0.4, isTextBox: true, margin: 0, align: "center", valign: "middle",
      fontFace: "Calibri", fontSize: 14, bold: true, color: WHITE });
    s.addText(t, { x: 1.55, y: y + 0.12, w: 4.6, h: 0.75, isTextBox: true, margin: 0, valign: "middle",
      fontFace: "Calibri", fontSize: 14, bold: true, color: TEXT });
    s.addText(d, { x: 6.3, y: y + 0.12, w: 6.2, h: 0.75, isTextBox: true, margin: 0, valign: "middle",
      fontFace: "Calibri", fontSize: 11.5, color: MUTED, lineSpacing: 14 });
    y += 1.18;
  });
  s.addText("The reconciliation test's own first version failed — for a real reason, not a flaky test. Documented in the report, not smoothed over.",
    { x: 0.6, y: 6.75, w: 12.1, h: 0.5, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 12.5, italic: true, color: TERRA });
  pageNum(s, 6);
}

// ---------- Slide 7: what ships ----------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "What Ships", "Live, not local — CI, hosted docs, a real dashboard");

  const cards = [
    { t: "Continuous Integration", d: "GitHub Actions runs the full daily cycle on push, PR, a daily schedule, and manual dispatch — generate, load, build, test, publish.", url: "github.com/EileenIp/ad-creative-pipeline" },
    { t: "Public Lineage Docs", d: "dbt docs, self-contained and hosted — the raw → staging → marts graph is publicly browsable, not a screenshot.", url: "eileenip.github.io/ad-creative-pipeline" },
    { t: "Live Thin Dashboard", d: "Freshness, a defect log, and top-decile creatives — generated fresh every CI run, not a local-only demo.", url: "eileenip.github.io/ad-creative-pipeline/dashboard" },
  ];
  const cw = 3.95, gap = 0.2, x0 = 0.6, y0 = 2.1, ch = 4.2;
  cards.forEach((c, i) => {
    const x = x0 + i * (cw + gap);
    s.addShape("roundRect", { x, y: y0, w: cw, h: ch, rectRadius: 0.12, fill: { color: OFFWHITE }, line: { color: "E3E2DE", width: 1 } });
    s.addShape("ellipse", { x: x + 0.3, y: y0 + 0.3, w: 0.22, h: 0.22, fill: { color: TERRA }, line: { type: "none" } });
    s.addText(c.t, { x: x + 0.3, y: y0 + 0.65, w: cw - 0.6, h: 0.9, isTextBox: true, margin: 0,
      fontFace: "Cambria", fontSize: 17, bold: true, color: TEXT, lineSpacing: 20 });
    s.addText(c.d, { x: x + 0.3, y: y0 + 1.55, w: cw - 0.6, h: 1.9, isTextBox: true, margin: 0,
      fontFace: "Calibri", fontSize: 12.5, color: MUTED, lineSpacing: 17 });
    s.addText(c.url, { x: x + 0.3, y: y0 + ch - 0.55, w: cw - 0.6, h: 0.4, isTextBox: true, margin: 0,
      fontFace: "Calibri", fontSize: 10.5, color: TERRA, bold: true });
  });
  pageNum(s, 7);
}

// ---------- Slide 8: close ----------
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  motifCircles(s, { color: TERRA });
  s.addText("WHAT THIS PROVES", { x: 0.6, y: 0.7, w: 10, h: 0.5, isTextBox: true, margin: 0,
    fontFace: "Calibri", fontSize: 14, bold: true, color: TERRA, charSpacing: 1.5 });
  s.addText("Engineering depth is in what a pipeline refuses to paper over.",
    { x: 0.6, y: 1.25, w: 11.5, h: 1.1, isTextBox: true, margin: 0, fontFace: "Cambria", fontSize: 30, bold: true, color: WHITE, lineSpacing: 33 });

  const closers = [
    "Three defect types stay visible on purpose — not silently “fixed” into a number the platform never actually delivered.",
    "The lookback window and dedup rule are both derived and stated, not defaulted — every number here has a reason attached.",
    "The reconciliation test's own build history — a real failure, fixed for a real reason — is in the commit log, not smoothed over in this deck.",
  ];
  let y = 2.9;
  closers.forEach((t) => {
    s.addShape("ellipse", { x: 0.65, y: y + 0.08, w: 0.14, h: 0.14, fill: { color: TERRA }, line: { type: "none" } });
    s.addText(t, { x: 0.95, y, w: 11.5, h: 0.9, isTextBox: true, margin: 0, fontFace: "Calibri", fontSize: 15, color: ICE, lineSpacing: 20 });
    y += 1.05;
  });

  s.addText("github.com/EileenIp/ad-creative-pipeline", { x: 0.6, y: H - 0.85, w: 8, h: 0.4, isTextBox: true, margin: 0,
    fontFace: "Calibri", fontSize: 13, color: "9BAAD8" });
}

pres.writeFile({ fileName: "deliverables/same-day-reliability-deck.pptx" }).then(() => {
  console.log("Wrote deliverables/same-day-reliability-deck.pptx");
});
