# Deployment guide — Australian Data Centre Atlas

Step-by-step, from the folder on your PC to a live GitHub Pages site with daily automatic updates.
Written for Windows 10/11. Time needed: about 20 minutes the first time.

---

## 0. What you are deploying

```
au-dc-dashboard/
├── data/source/ADC_Master_YYYYMMDD.xlsx   ← the ONE file you edit (all facts live here)
├── data/archive/                          ← frozen older workbooks (created by new_version.py)
├── scripts/                               ← build_data.py, fetch_news.py, fetch_geo.py, new_version.py
├── site/                                  ← the static website (index.html + assets + data/*.json)
├── .github/workflows/build-deploy.yml     ← GitHub Actions: build → fetch news/GIS → deploy
├── DEPLOY_GUIDE.md  DATA_UPDATE_GUIDE.md  README.md
└── docs/                                  ← research notes, GIS source documentation
```

The website is pure static files (no server, no database). GitHub Pages hosts it for free; GitHub Actions
rebuilds it whenever you push a change and once a day on a schedule (news + GIS refresh).

---

## 1. One-time setup on your PC

1. **Install Git for Windows** — https://git-scm.com/download/win (accept defaults).
2. **Install GitHub Desktop** (optional but easiest) — https://desktop.github.com/ — sign in with your GitHub account.
3. **Install Python 3.12+** — https://www.python.org/downloads/windows/ — tick **"Add python.exe to PATH"** during install.
4. Open **PowerShell** in the project folder (Shift + right-click the folder → *Open PowerShell window here*) and run:
   ```powershell
   pip install -r scripts\requirements.txt
   python scripts\build_data.py
   ```
   You should see `wrote facilities.json …` lines. This proves the pipeline works locally.
5. **Preview locally** (optional):
   ```powershell
   python -m http.server -d site 8000
   ```
   then open http://localhost:8000 in your browser. Stop with Ctrl+C.
   (Opening `site\index.html` directly from Explorer will *not* work — browsers block `fetch()` from `file://`.)

---

## 2. Create the GitHub repository

### Option A — GitHub Desktop (recommended)
1. GitHub Desktop → **File → Add local repository** → choose the `au-dc-dashboard` folder → *create a repository* when prompted (name: `au-dc-dashboard`, keep "Initialize with README" **unticked**).
2. Bottom-left: type a summary such as `Initial dashboard` → **Commit to main**.
3. Top bar: **Publish repository** → untick *Keep this code private* **only if** you want the site public (see §5 on visibility) → **Publish**.

### Option B — command line
```powershell
cd path\to\au-dc-dashboard
git init -b main
git add .
git commit -m "Initial dashboard"
gh repo create au-dc-dashboard --private --source=. --push      # needs GitHub CLI (winget install GitHub.cli), or:
# git remote add origin https://github.com/<your-user-or-org>/au-dc-dashboard.git
# git push -u origin main
```

---

## 3. Turn on GitHub Pages (via Actions)

1. On github.com open the repository → **Settings → Pages**.
2. Under **Build and deployment → Source** choose **GitHub Actions** (not "Deploy from a branch").
3. Go to **Settings → Actions → General → Workflow permissions** → select **Read and write permissions** → Save.
   (The daily job commits the refreshed `news.json` and GIS files back into the repo.)
4. Open the **Actions** tab → *Build data & deploy to GitHub Pages* → **Run workflow** → tick *Force re-download of GIS layers* → **Run workflow**.
5. Wait ~2–4 minutes. The run has two jobs (`build`, `deploy`); when both are green, the site URL appears on the `deploy` job and under Settings → Pages:

   `https://<your-user-or-org>.github.io/au-dc-dashboard/`

That first run downloads the Geoscience Australia transmission lines / substations and TeleGeography submarine cables (they cannot be fetched from a normal office network in some organisations, which is why the Action does it).

---

## 4. Daily automation — what happens without you

| When | What |
|---|---|
| Every push to `main` | `build_data.py` (workbook → JSON) → `fetch_news.py` → deploy |
| Daily 21:00 UTC (07:00 AEST) | same, plus `fetch_news.py` merges new headlines from the RSS feeds in the **NewsSources** sheet |
| Mondays (scheduled run) | `fetch_geo.py` refreshes GIS layers |
| Manual: Actions → Run workflow | any time; tick the box to force a GIS refresh |

GitHub disables scheduled workflows in repositories with **no activity for 60 days**. If the news stops updating, open the Actions tab and click **Enable workflow** (or just push any change).

---

## 5. Visibility and access

* **Private repository + GitHub Pages** requires GitHub **Pro / Team / Enterprise** (Pages on private repos is a paid feature). On a free plan the *repository* must be public for Pages to work — the site is public either way unless you are on Enterprise Cloud with "private Pages" access control.
* If the content must stay internal, alternatives: (a) GitHub Enterprise private Pages; (b) keep the repo private and publish the `site/` folder to an internal server or SharePoint via the same scripts; (c) Cloudflare Pages / Netlify with password protection (both can build from the same repo — run `pip install openpyxl && python scripts/build_data.py && python scripts/fetch_news.py` as the build command and `site` as the output directory).

---

## 6. Custom domain (optional)

Settings → Pages → **Custom domain** → e.g. `dcatlas.maicapital.com` → add a CNAME record at your DNS provider pointing to `<user-or-org>.github.io` → tick *Enforce HTTPS* once the certificate is issued. Add a file `site/CNAME` containing the domain so redeploys keep it.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| Action fails at *Build JSON*: `Workbook is missing sheets` | A sheet tab was renamed. Restore the original names (see README sheet in the workbook). |
| Action fails at *Build JSON*: `No ADC_Master_*.xlsx` | The workbook must be in `data/source/` and named `ADC_Master_<YYYYMMDD>.xlsx`. |
| `~$ADC_Master_….xlsx` appears in git | Excel lock file — close Excel; it is ignored by `.gitignore` anyway. |
| Site loads but map is blank | Basemap tiles come from CARTO/OpenStreetMap — check the network isn't blocking `basemaps.cartocdn.com`. |
| "Transmission lines" layer greyed out | `fetch_geo.py` hasn't run yet — Actions → Run workflow with *Force re-download*. |
| News never changes | Check Settings → Actions → Workflow permissions = *Read and write*; check the workflow isn't disabled after 60 days of inactivity. |
| Push rejected: "remote contains work" | The Action committed refreshed data. Run `git pull --rebase` (or *Pull origin* in GitHub Desktop) then push again. |
