# pdonta.github.io

Personal academic site. Jekyll on GitHub Pages, with the publication list
rebuilt automatically each week from your ORCID record.

---

## One setting you must change

Go to **Settings → Pages → Build and deployment → Source** and switch it from
*Deploy from a branch* to **GitHub Actions**.

This site builds itself through a workflow (that's what fetches ORCID before
each build). If Source stays on "Deploy from a branch", the workflow will run
but its output will never be published.

After changing it, open the **Actions** tab, choose **Build and deploy**, and
click **Run workflow**. The first run takes a few minutes because it fetches
every DOI from Crossref. Later runs are fast — results are cached.

---

## Where the content lives

Everything you'll edit is in `_data/`. No HTML, no CSS.

| File | Holds |
|---|---|
| `_data/site.yml` | Your name, title, contact details, external links, the menu |
| `_data/home.yml` | Home page statement, the four figures, background paragraphs |
| `_data/research.yml` | Interests, projects, directions, collaborations |
| `_data/teaching.yml` | Courses, PhD students, theses, openings |
| `_data/service.yml` | Editorial boards, calls, committees, memberships |
| `_data/news.yml` | News and talks |
| `_data/cv.yml` | Positions, education, awards |
| `_data/gallery.yml` | Photo albums |
| `_data/extra_publications.yml` | Books and anything ORCID doesn't have yet |
| `_data/publications.yml` | **Generated. Do not edit.** |

Edit any of them on GitHub with the pencil icon, commit, and the site rebuilds
in about a minute.

Two YAML rules cause nearly every problem:

- Indent with **two spaces**, never tabs.
- Wrap a value in `"quotes"` if it contains a colon.

If a build fails, the Actions tab shows the error.

---

## How publications work

`scripts/sync_orcid.py` runs before every build:

1. Reads your ORCID record for the list of works.
2. For each work with a DOI, fetches the full record: **Crossref** for
   journal and conference DOIs, **DataCite** for arXiv and Zenodo ones
   (`10.48550`, `10.5281`). This is why arXiv preprints now get proper
   author lists — Crossref doesn't hold them, DataCite does.
3. Picks up the citation count while it's there, shown as "Cited by N".
4. **Removes duplicate preprints.** When the same title exists as both an
   arXiv preprint and a published paper, only the published version is kept.
   Matching ignores case and punctuation, so "Self-Healing: A Survey" and
   "self healing a survey" count as the same work.
5. Merges in anything listed in `_data/extra_publications.yml`.
6. Caches lookups in `.cache/crossref.json`, so a weekly run only fetches
   what's new.
7. Writes `_data/publications.yml`, grouped into journal articles, books,
   chapters, conference papers and preprints.

Your own name is bolded automatically in every author list.

### Books and works not in ORCID

Put them in `_data/extra_publications.yml`. This is where the two Springer
books currently live. **Delete an entry from that file once it appears in
ORCID with a DOI**, otherwise it shows up twice.

### Choosing what appears on the home page

By default the home page shows the three most recent entries under "Selected
work". To choose them yourself, list DOIs under `featured_dois:` in
`_data/home.yml` — useful for leading with your strongest papers rather than
the newest. Leave the list empty to go back to automatic.

**To fix a wrong entry, fix it in ORCID, not here.** Anything you change in
`_data/publications.yml` is overwritten on the next run.

Works without a DOI still appear, using whatever ORCID holds — usually title,
year and journal name, but no authors. If a paper is missing entirely, it's
missing from your ORCID record.

The schedule is Mondays at 04:00 UTC, set in
`.github/workflows/build.yml`. You can also trigger it any time from the
Actions tab.

---

## Common edits

**Add a talk or a news item.** Open `_data/news.yml` and copy the commented
block at the bottom. `kind` can be Talk, News, Award, Paper or Visit.

**Add a gallery album.** Create `assets/img/gallery/<name>/`, upload photos,
then add a block to `_data/gallery.yml` listing the filenames. Resize large
photos first — anything over about 1500px wide just slows the page down.

**Change your photo.** Replace `assets/img/portrait.jpg`, keeping the
filename. A square image of roughly 900×900 works best. The current one is
from 2019 and should be swapped for your SU profile photo.

**Add your CV as a PDF.** Put it at `assets/doc/cv.pdf`. The link on the CV
page is already pointing there.

**Remove a page.** Delete its line from the `nav:` list in `_data/site.yml`.
The page still exists but disappears from the menu.

---

## A note on the old PHP site

Do not upload the old `htdocs` folder to this or any public repository.
`htdocs/config.php` contains a plaintext database password and
`htdocs/lin/.htpasswd` contains a password hash. That password should be
treated as compromised and changed anywhere it was reused.

---

## Previewing locally (optional)

Not needed — editing on GitHub works fine. But if you want to:

```bash
bundle install
pip install pyyaml
python3 scripts/sync_orcid.py    # optional, refreshes publications
bundle exec jekyll serve
```

Then open `http://localhost:4000`.
