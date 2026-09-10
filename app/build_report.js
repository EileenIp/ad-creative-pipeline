const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, convertInchesToTwip,
} = require("docx");
const fs = require("fs");

const ACCENT = "B5541C";
const MUTED = "6B6B66";
const TEXT = "1F1F1D";

const numbering = {
  config: [
    {
      reference: "bullets",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: convertInchesToTwip(0.35), hanging: convertInchesToTwip(0.2) } } } },
      ],
    },
  ],
};

function h1(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_1, outlineLevel: 0, spacing: { before: 360, after: 160 } });
}
function h2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, outlineLevel: 1, spacing: { before: 260, after: 120 } });
}
function p(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, italics: opts.italics, bold: opts.bold, color: opts.color })],
    spacing: { after: 160 },
  });
}
function bullet(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, italics: opts.italics })],
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 100 },
  });
}
function rule() {
  return new Paragraph({
    text: "",
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "E3E2DE", space: 4 } },
    spacing: { after: 200 },
  });
}
function statCell(value, label, width) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    margins: { top: 160, bottom: 160, left: 160, right: 160 },
    children: [
      new Paragraph({ children: [new TextRun({ text: value, bold: true, size: 32, color: ACCENT })] }),
      new Paragraph({ children: [new TextRun({ text: label, size: 18, color: MUTED })] }),
    ],
  });
}

const statRowWidth = convertInchesToTwip(1.6) ;

const doc = new Document({
  numbering,
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 22, color: TEXT } },
      heading1: { run: { bold: true, size: 30, color: TEXT, font: "Cambria" },
        paragraph: { spacing: { before: 360, after: 160 } } },
      heading2: { run: { bold: true, size: 24, color: ACCENT, font: "Cambria" },
        paragraph: { spacing: { before: 260, after: 120 } } },
    },
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 },
        },
      },
      children: [
        new Paragraph({
          children: [new TextRun({ text: "SAME-DAY NUMBERS YOU CAN ACTUALLY TRUST", bold: true, size: 40, color: TEXT })],
          spacing: { after: 80 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "Ad Creative Performance Pipeline — an openly synthetic, deliberately hostile dbt-core + DuckDB pipeline", size: 24, color: MUTED })],
          spacing: { after: 40 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "github.com/EileenIp/ad-creative-pipeline  ·  eileenip.github.io/ad-creative-pipeline", size: 20, color: MUTED, italics: true })],
          spacing: { after: 300 },
        }),
        rule(),

        h1("Executive Summary"),
        p("Media buyers usually find out which creatives are winning a week after the numbers mattered. This project asks a narrower, more honest question: not “which creative won,” but “can a pipeline be trusted to say so on the day it happens — even when the upstream data misbehaves?” The deliverable is the pipeline, not an advertising finding."),
        p("Real creative-level ad performance data isn't published anywhere — not even the Facebook Ad Library exposes performance, only creative content. So this project generates openly synthetic data and injects 8 named defect types into it on purpose: late arrivals, restated numbers, exact and near duplicates, a schema change mid-stream, nulled fields, a clicks-exceed-impressions platform bug, and one day the platform never delivers at all. Every defect is logged to a ground-truth manifest, so the pipeline's handling of each one can be checked against a known answer, not eyeballed."),
        p("The result reconciles to that ground truth exactly, with one distinction that matters more than the reconciliation itself: three of the eight defect types are never corrected by the upstream platform, and a pipeline that quietly “fixed” them would be inventing numbers. The other five — including a missing day that turned out to also swallow nearby late-arriving rows, a real finding documented below — resolve correctly through a stated 7-day lookback window and a stated dedup rule.", {}),
        p("Built with dbt-core and DuckDB, orchestrated by GitHub Actions: 10 dbt tests (one configured to warn on purpose), a publicly hosted lineage graph, and a live thin dashboard — not a local-only demo."),

        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          borders: {
            top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
            left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
            insideHorizontal: { style: BorderStyle.NONE }, insideVertical: { style: BorderStyle.NONE },
          },
          rows: [
            new TableRow({ children: [
              statCell("484", "creatives / 25 campaigns", statRowWidth),
              statCell("25,892", "ground-truth rows", statRowWidth),
              statCell("8", "named defect types, all logged", statRowWidth),
              statCell("10", "dbt tests, all green (1 by-design warn)", statRowWidth),
            ]}),
          ],
        }),
        new Paragraph({ text: "", spacing: { after: 300 } }),

        h1("Findings"),

        h2("The hostile-input design"),
        p("A generator (src/generator.py, fixed seed) produces the correct, never-corrupted ground truth first — 484 creatives across 25 campaigns over a 95-day window — then corrupts it on delivery across 96 daily drop files. Every corruption is logged: 2,656 late-arriving rows, 1,260 restated rows, 109 exact and 111 near duplicates, 276 nulled fields, 78 rows where clicks exceed impressions, 1 schema-drift event, and 1 day the platform never delivers at all. That's 4,492 individually logged defect events against 25,892 true rows — a genuinely hostile upstream, not a token one."),

        h2("Reconciliation, reported honestly"),
        p("Not every defect is supposed to self-heal, and treating all eight the same would be dishonest about what the pipeline actually does:"),
        bullet("Late arrivals, restatements, and cross-file duplicates self-heal. The platform eventually delivers a correct, unambiguous version, and the pipeline's dedup (latest-delivery-wins) plus a 7-day lookback window converge on it."),
        bullet("Nulled fields and the clicks-exceed-impressions bug do not. The generator never issues a correction for either — a pipeline that made these match ground truth would be inventing numbers. Instead they're surfaced: a dedicated test (assert_clicks_lte_impressions) is configured to warn every run, finding roughly 76–78 rows exactly as designed."),
        bullet("Same-file near-duplicates are a documented ambiguity, not a bug. When two candidate rows for one key arrive in the same file, there's no signal for which is “truer.” The surviving value is an arbitrary but deterministic tiebreak, and a dedicated column (had_same_drop_duplicate) makes that visible rather than hiding it."),

        h2("The missing-day finding"),
        p("One day the platform never delivers at all — not late, permanently absent. The pipeline correctly shows no data for it. What's less obvious, and worth stating plainly to a BI lead: the damage isn't limited to that one day. Of the 281 rows the pipeline could never reconcile to ground truth, 253 were on the missing day itself — but 28 more were late-arriving rows from the three days before it, scheduled for delivery on that exact date, that vanished along with everything else. A platform outage doesn't just cost the day it happens on."),

        h2("The test suite as the safety net"),
        p("10 dbt tests run on every build: uniqueness and not-null checks on keys, referential integrity between the fact and dimension tables, the by-design warn-severity clicks/impressions test, and a reconciliation test scoped to the lookback window that compares the pipeline's own output against the generator's ground truth. That last test's first version genuinely failed — documented in full in the Appendix — for a real modeling reason, not a bug in the test itself."),

        h1("What This Means for Same-Day Reporting"),
        p("In plain terms: this pipeline proves it can tell the difference between data that will get better on its own and data that won't. Late-arriving and restated numbers self-heal within a week without anyone doing anything; a clicks-exceed-impressions bug or a lost day does not, and the pipeline says so out loud through a defect log and a two-number freshness indicator — a “latest finalized day” that's guaranteed final, and a “latest available day” that's still provisional — rather than a single, silently-wrong number."),
        p("A BI lead reading this pipeline's output can trust the finalized number completely and knows exactly why the provisional one might still move. The CTR/CPC/CPA figures themselves are not a finding about advertising — they're synthetic, stated as such on every surface — the thing being sold here is the reliability discipline, not an insight."),

        h1("Limitations"),
        p("Drafted from findings already established in this project; where a judgment call genuinely needs Eileen's own reasoning to be defensible in an interview, that's flagged explicitly below rather than presented as settled.", { italics: true, color: MUTED }),
        bullet("Openly synthetic upstream by design. No real advertising platform's performance data is used or claimed anywhere in this project — the CTR/CPC/CPA numbers are plumbing-test water, not an advertising finding."),
        bullet("Single-platform schema, invented for this project. A real Meta or Google Ads export changes three concrete things: the column set (Meta's Marketing API returns nested insight objects per ad, not a flat CSV — impressions/clicks/spend live under an “insights” edge keyed by date range, and creative metadata is a separate object joined by ad ID); the auth flow (OAuth2 with a refreshable long-lived token, not a filesystem drop — the loader's “pick up new files” model becomes “poll an API on a schedule and handle token expiry”); and rate limits (Meta's Marketing API enforces a rolling points-based budget per ad account, so a same-day pull for many accounts needs backoff and batching designed in from the start, not bolted on after a 429). None of this changes the staging/marts layer — dedup, lookback, and the metric definitions are platform-agnostic by construction — it only changes the loader."),
        bullet("DuckDB won't be the right engine forever, and knowing where it stops matters more than defending it as a permanent choice. DuckDB is single-node and in-process — no distributed query engine, no built-in multi-writer concurrency. In practice that's comfortable well into the tens of gigabytes on a single modern machine, which covers this project by a wide margin (the actual warehouse here is a few megabytes) and would still comfortably cover a single mid-size advertiser's full creative-performance history. The real switch point isn't a row count — it's needing concurrent writers (multiple pipelines landing data at once), needing compute larger than one machine can hold in memory, or needing the warehouse to serve many analysts' ad-hoc queries at once without one heavy query blocking another. BigQuery (or Snowflake) earns its cost at that point, not before it — and dbt models port across both with only the adapter and a handful of engine-specific functions changing, which is exactly why DuckDB was a safe choice to prototype with."),
        bullet("Top-decile ranking rounds coarsely on small same-day campaign groups. percent_rank's granularity means the flagged share runs closer to 12–18% than an exact 10% for campaigns with fewer than roughly 10 eligible creatives on a given day — worth knowing before reading too much into the exact count on a slow day."),

        h2("Next steps"),
        bullet("Point the loader at a real Meta or Google Ads export in a sandboxed ad account — the staging and marts layers shouldn't need to change; the loader will."),
        bullet("Add a persisted, run-over-run metrics table (defect counts, reconciliation pass/fail, test results) so the dashboard can show a trend, not just a snapshot."),
        bullet("Revisit the DuckDB-to-BigQuery decision once (or if) a real deployment needs concurrent writers or multi-analyst load — not before."),

        h1("Appendix: Method"),

        h2("Lookback window and dedup rule"),
        p("The incremental staging model reprocesses a 7-day lookback window on every run, via delete+insert rather than pure append. The number is derived, not assumed: the generator's worst-case corruption lag is a 3-day late arrival plus a restatement correction up to 2 more days on top of that — 5 days — and 7 adds a 2-day margin. A shorter window (3 days, the other number considered) would silently miss the worst-case restatement corrections, which would undercut the project's own “reliable same-day numbers” pitch; the reprocessing cost of the wider window is negligible on local DuckDB, so correctness won the trade."),
        p("Dedup rule: latest delivery wins. When two rows share a key within the same file (an exact or near duplicate), a deterministic tiebreak by row position resolves it — an arbitrary but reproducible choice, not a claim about which of two same-key rows is “truer,” since the data itself doesn't say."),

        h2("Ranking metric and volume floor"),
        p("Top-decile flagging uses CTR alone, chosen for simplicity over CPA or a blended score, scoped to (campaign, day). A creative must clear a 1,000-daily-impression floor to be eligible — chosen from the data's own distribution (close to the observed 10th percentile of daily impressions, leaving roughly 91% of creative-days still eligible) so a handful of impressions can't “win” the ranking by accident."),

        h2("Three bugs, found and fixed"),
        p("Real engineering problems surfaced during the build and were corrected before anything shipped — documented here because catching them is part of the actual work, not a footnote.", {}),
        bullet("An untracked empty directory silently broke the first real CI run. dbt/seeds/ only ever contained a gitignored CSV, and git doesn't track empty directories — so a fresh checkout had no dbt/seeds/ at all, and the workflow's plain copy step into it failed outright, skipping dbt seed and dbt build entirely. Local testing never caught it, because the directory already existed locally from earlier manual runs. Fixed with a tracked .gitkeep placeholder plus a defensive mkdir -p."),
        bullet("A settings-page click that looked like it worked, didn't. Enabling GitHub Pages is a repo-settings change outside the build agent's permission scope, so it had to be done by hand — and the first attempt silently didn't save, with no indication from the GitHub web UI that anything was wrong. Caught by querying the GitHub API directly instead of trusting the settings page, twice, before the second attempt was confirmed to have actually taken."),
        bullet("The dashboard's results table broke on an actual mobile viewport, not in theory. It overflowed the page instead of scrolling within itself at 375px width — caught by checking a real mobile viewport before shipping, not assumed fine because it looked fine on desktop. Fixed with a scoped overflow-x: auto wrapper."),

        h2("The reconciliation test's own bug"),
        p("The first version of the reconciliation test failed — 7 rows, later 1 — for a real modeling reason, not a flaky test. It expected every defect type to match ground truth once dedup and the lookback window were in place. That's wrong: nulled fields, the clicks-exceed-impressions bug, and same-file near-duplicates are never corrected by the generator, so forcing them to reconcile would mean inventing numbers. Fixed by scoping the comparison to defects that genuinely do resolve (late arrival, restatement, cross-file duplicates), and by adding a real had_same_drop_duplicate column so the near-duplicate ambiguity is visible in the data rather than silently resolved. The fix changed what the test checks, not the threshold for passing it."),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("deliverables/same-day-reliability-report.docx", buf);
  console.log("Wrote deliverables/same-day-reliability-report.docx");
});
