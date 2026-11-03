# What runs by itself

Three scheduled jobs keep the site current. Two are fully automatic; the third hands you a review queue
rather than editing the database, because facility and operator figures need judgement that a script
cannot supply.

| When | Job | What it does | Touches your data? |
|---|---|---|---|
| Every day, 21:00 UTC (07:00 AEST / 08:00 AEDT) | `build-deploy.yml` | Collects the day's Australian data centre headlines and appends them to the archive, rebuilds all JSON from the workbook, redeploys the site | No — news only |
| Mondays (same run) | `build-deploy.yml` | Refreshes transmission lines, substations and submarine cables from Geoscience Australia and TeleGeography | No |
| 1st of each month, 22:00 UTC (09:00 AEDT) | `monthly-review.yml` | Reads last month's headlines, works out which facilities and operators they concern, opens a GitHub issue listing what probably needs changing, and opens a new time-stamped edition of the workbook for those changes to go into | Creates the new edition; **changes no figures** |
| 2nd of each month, 22:00 UTC (09:00 AEDT on the 3rd) | `monthly-refresh.yml` | Claude researches the queue, edits the new workbook edition and opens a **pull request** | Only on a branch — never on `main` |
| Every push | `build-deploy.yml` | Rebuild and redeploy | No |

---

## The news archive grows, it never shrinks

`scripts/fetch_news.py` appends. Each run adds headlines it has not seen before and leaves everything
already collected untouched — there is no pruning and no cap. Over a year that is roughly 700–900 items
and under 500 KB, which the page loads comfortably.

De-duplication is by link and by normalised headline, so the same story arriving through two feeds
(or the same feed on consecutive days) lands once. Every item records `first_seen`, which is what the
monthly review uses to answer "what arrived since last time".

**On the site** the News tab opens on a recent window — the last `news_days_to_keep` days from the Meta
sheet, 90 by default — and shows 60 headlines at a time, with *Show 60 more* and *Show the full archive*
beneath. The window is a display choice only; nothing is deleted.

### Changing what gets collected
Edit the **NewsSources** sheet in the workbook. One row per feed:

- `url` — any RSS or Atom feed. Google News queries work well:
  `https://news.google.com/rss/search?q=<query>&hl=en-AU&gl=AU&ceid=AU:en`
- `filter_keywords` — comma-separated; for a broad feed like Data Center Dynamics this keeps only
  Australian items. Leave blank to take everything.
- `enabled` — `FALSE` pauses a feed without deleting the row.

Save the workbook under a new date, upload it to `data/source/`, and the next run uses the new list.
A feed that errors is skipped and logged in `news.json` under `errors`; it never fails the build.

---

## The monthly review issue

On the 1st you get an issue titled **"Monthly data review — 2026-11"**. It contains, as tick-boxes:

1. **Facilities named in the news.** Only where the headline genuinely identifies one. Matching uses
   tokens that are distinctive to a single facility — "Glendenning" or "Kurri" identify; "Sydney",
   "Melbourne" and "NEXTDC" appear in dozens of names and identify nothing — and needs either two
   distinctive tokens or one plus the operator's name. It is deliberately conservative: a missed match
   lands in the operator section rather than being attached to the wrong site.
2. **Operators named in the news**, grouped by company.
3. **Regulation and grid** headlines.
4. **Regulatory dates that have now passed** — scraped from the dates written into your regulation
   steps, so "final determination due 29 Oct 2026" surfaces in November for you to record the outcome.
5. **Pipeline rows not re-verified in 90+ days**, largest first, limited to projects still moving.

Work through it, edit the workbook, save under a new date, upload to `data/source/`. The site rebuilds
and the old workbook archives itself. Close the issue when done.

Run it early or over a custom range from **Actions → Monthly data review → Run workflow** — it takes
optional `since` and `until` dates.

Each brief is also committed to `review/YYYY-MM.md`, so you keep the history.

### The workbook rolls with the review
On the 1st, after writing the brief, the job copies `data/source/<PREFIX>_<YYYYMMDD>.xlsx` to that day's
name and commits it. The next build moves the superseded file into `data/archive/` and rebuilds from the
new one, so versioning and archiving need no clicks from you. The review issue names the edition to edit.

The site's **Database as of** stamp is that filename's date — not a cell anyone has to remember to update.
Upload a workbook with a new date and the header follows it; the Meta sheet's `data_as_of` is only a
fallback for a file whose name carries no stamp.

The roll is skipped when the review queued nothing, so a quiet month leaves the stamp where it is: the
date never advances on a database that has not changed. The new edition starts as an exact copy of the old
one — same rows, same figures, one extra Changelog line recording the roll and what the queue contained.

## The refresh works the queue, and asks before it lands
On the 2nd, `monthly-refresh.yml` runs Claude against the brief the review wrote the day before. It
researches each queued item against primary sources, edits the month's workbook edition in place,
rebuilds the JSON, and opens a pull request. It cannot write to `main`.

Before the pull request is opened, `scripts/validate_edition.py` compares the edition against the one
it supersedes and refuses to proceed if the result is not sound: a facility row has disappeared, a
sheet has lost rows, the headline IT-load movement does not reconcile to a named list of facilities,
more than 40 facility rows changed, or the headline swung more than 25%. The reconciliation goes in
the pull request body, so the first thing you read is which facility moved the number and why.

**Review the JSON, not the workbook.** The `.xlsx` is a binary and GitHub cannot diff it. The pull
request carries the rebuilt `site/data/*.json`, where every changed field shows up as a readable
line. Merging triggers the ordinary build, which archives the superseded workbook and deploys.

The prompt tells Claude to verify rather than transcribe, to leave undisclosed figures blank rather
than estimate, to set `capacity_basis` when a source publishes site demand instead of IT load, and
to write down what it was unsure about. That last instruction matters: the October 2026 queue got
four of its six framings wrong, and the value of the run is in catching that, not in covering every
headline.

**Setup, once:** add a repository secret under Settings -> Secrets and variables -> Actions, named
either `CLAUDE_CODE_OAUTH_TOKEN` (run `claude setup-token` locally; billed to your Claude
subscription) or `ANTHROPIC_API_KEY` (billed to API credit). The workflow stops with a clear message
if neither is set, and skips entirely in a month where the review queued nothing.

### What it deliberately does not do
It never edits the workbook, the JSON or the site. Capacity figures, stages, ownership and regulatory
text are the numbers you would put in front of an investment committee; a keyword matcher has no business
setting them. The job's value is that it reads a month of news so you don't have to, and hands you a
short list with the links already attached.

---

## Things to know

- **Scheduled workflows pause after 60 days of repository inactivity.** GitHub emails you first. If the
  news stops updating, open the **Actions** tab and click **Enable workflow**, or push any change.
- **Daily runs that find nothing new commit nothing** — that is normal, not a failure.
- **Check on it**: the News tab shows "last refreshed"; the Actions tab shows every run; `news.json`
  carries `per_source` counts and any feed errors from the most recent run.
- **Free-tier minutes**: these jobs use roughly 3–5 minutes a day on a public repository, where Actions
  minutes are unlimited. On a private repository it is well inside the monthly free allowance.
- **Only the refresh needs a credential.** News, GIS, the review, the roll, the build and the deploy all run on
  nothing but GitHub. `monthly-refresh.yml` is the one job that needs `CLAUDE_CODE_OAUTH_TOKEN` or
  `ANTHROPIC_API_KEY`; without it that job stops with a clear message and everything else carries on.
