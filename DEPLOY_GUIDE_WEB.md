# Deploy from the GitHub website — no Git, no GitHub Desktop

Everything below happens in a browser. About 15 minutes the first time.
(The GitHub Desktop route is still in `DEPLOY_GUIDE.md` if you ever want it.)

---

## Before you start

Unzip `au-dc-dashboard.zip` somewhere you can find it — say your Desktop. You will drag files
out of the unzipped **au-dc-dashboard** folder in step 3.

---

## 1. Create the repository

1. Go to https://github.com/new (sign in first).
2. **Repository name:** `au-dc-dashboard`
3. **Public** or **Private** — see the note at the bottom about Pages on private repos.
4. Tick **Add a README file**. (This matters: it creates the `main` branch so you can upload into it.)
5. **Create repository**.

## 2. Turn on Pages and write permissions

Do this before the first build so the first run works.

1. **Settings → Pages → Build and deployment → Source** → choose **GitHub Actions**. Nothing to save; it applies immediately.
2. **Settings → Actions → General** → scroll to **Workflow permissions** → select **Read and write permissions** → **Save**.
   (The daily job commits the refreshed news and map layers back into the repo, so it needs write access.)

## 3. Upload the site — one folder at a time

> **This is the step that trips people up.** If you select several folders at once, or files and folders
> together, the browser usually uploads only the loose files and silently drops the folders. The repository
> then looks almost right but the build has nothing to work with. Upload **one folder per commit**.

Do this four times — once for `site`, once for `scripts`, once for `data`, once for `docs`:

1. On the repository's **Code** tab: **Add file ▾ → Upload files**.
2. From your unzipped `au-dc-dashboard` folder, drag in **exactly one folder** — start with `site`. Nothing else selected.
3. Wait until the file list on the page stops growing (`site` is about 25 files), then **Commit changes**.
4. Go back to the **Code** tab and confirm the folder is now listed before moving to the next one.

Then upload the four loose files the same way, in one go: `README.md`, `DEPLOY_GUIDE.md`,
`DEPLOY_GUIDE_WEB.md`, `DATA_UPDATE_GUIDE.md`. (Files without folders upload fine together.)

Skip the `.github` folder — hidden folders are blocked by drag-and-drop, which is why the workflow file gets
typed in by hand in the next step. `.gitignore` is optional.

### If the folders still won't upload
Use GitHub's built-in web editor instead:

1. On the repository page, press the **`.`** key. A VS Code window opens in your browser (github.dev).
2. Drag the folders into the file explorer on the left.
3. Click the **Source Control** icon in the left sidebar, type a message, and click **Commit & Push**.

It handles folders far more reliably than the upload page, and it is still entirely browser-based.

## 4. Add the workflow file (this starts the first build)

1. **Add file ▾ → Create new file**.
2. In the filename box type exactly:

   ```
   .github/workflows/build-deploy.yml
   ```

   As you type each `/` GitHub turns it into a folder — that is what you want.
3. Open `.github/workflows/build-deploy.yml` from your unzipped folder in Notepad, copy all of it, and paste
   it into the big editing box. (Right-click the file → Open with → Notepad. Or use the copy I sent you in chat.)
   The workflow locates the project itself, so it works whether the files sit at the repository root or one
   folder down — a nested upload is not something you need to fix.
4. **Commit changes**.

Committing the workflow triggers the first run straight away.

## 5. Watch it build, then open the site

1. Go to the **Actions** tab. You should see a run called *Build data & deploy to GitHub Pages*.
2. It has two jobs, `build` then `deploy`, and takes 2–4 minutes. Both should go green.
3. When `deploy` finishes, your URL appears on that job and under **Settings → Pages**:

   `https://<your-username>.github.io/au-dc-dashboard/`

The first run also downloads the Geoscience Australia transmission lines and substations and the
TeleGeography submarine cables, so the extra map layers appear from the start.

---

## Updating the data later — also entirely in the browser

This is the part that matters month to month. You never need to delete or move anything.

1. On your PC, make the new version of the workbook. Easiest: open the current
   `data/source/ADC_Master_20261007.xlsx`, **Save As** with today's date in the name —
   `ADC_Master_20261104.xlsx` — and edit that copy.
2. In the repository, click into the **data** folder, then **source**.
3. **Add file ▾ → Upload files** → drag the new `ADC_Master_<date>.xlsx` in → **Commit changes**.
4. That's it. The workflow runs on the commit: it moves the older workbook into `data/archive/`
   automatically, rebuilds all the JSON, refreshes the news, and redeploys. Check the Actions tab if
   you want to watch; the site updates in 2–3 minutes.

The naming is what drives it — the build always uses the **newest `ADC_Master_<YYYYMMDD>.xlsx`** by the
date in the filename, so keep that format and the timestamps increasing.

### Editing one small thing without touching the workbook
Any text file can be edited in place: click the file, then the pencil icon, make the change, **Commit changes**.
Useful for `site/assets/i18n.js` (interface wording) or the guides. Don't hand-edit anything in `site/data/` —
those files are regenerated from the workbook on every build and your change would be overwritten.

### Forcing a refresh by hand
**Actions → Build data & deploy to GitHub Pages → Run workflow ▾**. Tick *Force re-download of GIS layers*
if you want the Geoscience Australia map layers pulled again.

---

## Things worth knowing

- **Scheduled runs pause after 60 days of no activity.** If the daily news stops updating, open the Actions
  tab and click **Enable workflow**, or just push any change.
- **Pages on a private repository needs GitHub Pro / Team / Enterprise.** On a free plan the repository must
  be public for the site to publish. The data here is compiled from public sources, but if it must stay
  internal: either upgrade the plan, or use Cloudflare Pages / Netlify with password protection — both can
  build from this same repository (build command `pip install openpyxl && python scripts/build_data.py && python scripts/fetch_news.py`, output directory `site`).
- **The 25 MB per-file limit** on web uploads is far above anything in this repo (the workbook is ~250 KB).
- **If the upload page stalls**, drag the folders in two batches — `site` on its own first, then the rest.

## If something goes wrong

| What you see | What to do |
|---|---|
| Actions run fails at *Install dependencies* with `Could not open requirements file` | The files landed one folder deep (the `au-dc-dashboard` folder was dragged in rather than its contents). The workflow now finds the project either way — make sure you are using the current `build-deploy.yml`. |
| Actions run fails at *Locate project root* | The folders didn't upload — the run log prints the repository listing, and you will see only the `.md` files. Go back to step 3 and upload `site`, `scripts`, `data` and `docs` **one folder per commit**. |
| Actions run fails at *Build JSON* with `No ADC_Master_*.xlsx` | The workbook didn't upload into `data/source/`. Check the folder on GitHub and re-upload. |
| Fails with `Workbook is missing sheets` | A sheet tab was renamed in Excel. Restore the original names (listed on the workbook's README sheet). |
| Fails at the commit step with a permissions error | Settings → Actions → General → Workflow permissions → **Read and write** → Save, then re-run. |
| `deploy` job fails with a Pages error | Settings → Pages → Source must be **GitHub Actions**, not "Deploy from a branch". |
| Site loads but the map tiles are blank | Your network is blocking `basemaps.cartocdn.com`. The markers still work; try another network. |
| Transmission-line layers greyed out | Actions → Run workflow, tick *Force re-download of GIS layers*. |
