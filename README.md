# Your personal site

A small Jekyll site for a résumé / portfolio, built to run on GitHub Pages
with no local install and no build step.

---

## Putting it online

**1. Create the repository.**
On GitHub, click **New repository**. Name it exactly:

```
yourusername.github.io
```

using your real GitHub username, all lowercase. The name is not cosmetic —
GitHub only treats a repo as your personal site if it matches your username
exactly. Set it to **Public** and don't add a README (you already have one).

**2. Upload these files.**
On the empty repo page, click **uploading an existing file**. Drag in
everything from this folder — including the `_layouts`, `_data`, and
`assets` folders. Then click **Commit changes**.

**3. Turn Pages on.**
Go to **Settings → Pages**. Under *Build and deployment*, set Source to
**Deploy from a branch**, branch **main**, folder **/ (root)**. Save.

**4. Wait a minute.**
Your site appears at `https://yourusername.github.io`. The first build
takes a couple of minutes; later ones are faster. If you see a 404, give
it five minutes before worrying.

---

## Changing the content

Almost everything lives in **`_data/resume.yml`**. Open it on GitHub, click
the pencil icon, edit, and commit. The site rebuilds automatically within
about a minute.

Then update **`_config.yml`** — the `title`, `description`, and `url` fields
are used for search engines and link previews, so they should match your
real name and username.

Two YAML rules that cause almost every problem:

- Indent with **two spaces**, never tabs.
- If a value contains a colon, wrap it in `"double quotes"`.

If the site stops rebuilding after an edit, YAML is the first place to
look. The Actions tab on your repo shows the build error.

---

## What each file does

| File | Purpose |
|---|---|
| `_data/resume.yml` | All your content. This is the one you'll edit. |
| `_config.yml` | Site title, description, URL. |
| `index.html` | Turns the data above into the page. |
| `_layouts/default.html` | The HTML shell — fonts, meta tags. |
| `assets/css/style.css` | All styling. Colours are at the top. |

---

## Adding a PDF résumé

Drop the file at `assets/resume.pdf` and the "Résumé (PDF)" link in
`_data/resume.yml` will work. Or delete that link entry — the page also
prints cleanly to PDF straight from your browser (Cmd/Ctrl + P), with the
layout adjusted for paper.

## Adding another page

Create a file like `writing.md` in the root with this at the top:

```
---
layout: default
title: Writing
---

Your text here, in Markdown.
```

It'll be served at `yourusername.github.io/writing`.

## A custom domain

If you own a domain, add a file named `CNAME` containing just the domain
name (e.g. `aminaortega.com`), then point your DNS at GitHub per their
custom-domain docs.

---

## Previewing locally (optional)

Not required — editing on GitHub works fine. But if you want a local
preview:

```bash
bundle install
bundle exec jekyll serve
```

Then open `http://localhost:4000`.
