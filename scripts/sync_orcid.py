#!/usr/bin/env python3
"""
Rebuild _data/publications.yml from an ORCID record.

ORCID is the source of truth for *which* works are yours. It does not,
however, store author lists. So for every work that carries a DOI we ask
Crossref for the full bibliographic record, and cache the answer in
.cache/crossref.json so later runs only fetch what is new.

Run:  python3 scripts/sync_orcid.py
Env:  ORCID_ID        override the iD in _config.yml
      CONTACT_EMAIL   sent to Crossref so we land in their polite pool
"""

import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_data" / "publications.yml"
CACHE = ROOT / ".cache" / "crossref.json"

# Whose name to bold in the author lists.
ME_FAMILY = "donta"
ME_GIVEN = "praveen"

# ORCID work types -> the heading they appear under, and the display order.
PREPRINT_TYPES = {"preprint", "working-paper"}

GROUPS = [
    ("Journal articles", {"journal-article"}),
    ("Books", {"book", "edited-book"}),
    ("Book chapters", {"book-chapter", "book-part"}),
    ("Conference papers", {"conference-paper", "conference-abstract",
                           "conference-poster", "lecture-speech"}),
    ("Preprints", {"preprint", "working-paper"}),
    ("Other", set()),  # catch-all, must stay last
]

TIMEOUT = 30


def get_json(url, headers=None, tries=3):
    req = urllib.request.Request(url, headers=headers or {})
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None          # genuinely absent, don't retry
            last = e
        except Exception as e:       # noqa: BLE001 - network is network
            last = e
        time.sleep(1.5 * (attempt + 1))
    print(f"  ! gave up on {url}: {last}", file=sys.stderr)
    return None


def read_orcid_id():
    if os.environ.get("ORCID_ID"):
        return os.environ["ORCID_ID"].strip()
    cfg = yaml.safe_load((ROOT / "_data" / "site.yml").read_text())
    orcid = (cfg or {}).get("orcid")
    if not orcid:
        sys.exit("No ORCID iD found. Set `orcid:` in _data/site.yml.")
    return str(orcid).strip()


def load_cache():
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text())
        except json.JSONDecodeError:
            print("  ! cache was corrupt, starting fresh", file=sys.stderr)
    return {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=0, sort_keys=True))


def fetch_orcid_works(orcid):
    url = f"https://pub.orcid.org/v3.0/{orcid}/works"
    data = get_json(url, {"Accept": "application/json"})
    if data is None:
        sys.exit(f"Could not read the ORCID record for {orcid}.")

    works = []
    for group in data.get("group", []):
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        s = summaries[0]

        title = (((s.get("title") or {}).get("title") or {}).get("value") or "").strip()
        if not title:
            continue

        year = None
        pubdate = s.get("publication-date") or {}
        if pubdate.get("year"):
            year = (pubdate["year"] or {}).get("value")

        doi = None
        for ident in ((group.get("external-ids") or {}).get("external-id") or []):
            if (ident.get("external-id-type") or "").lower() == "doi":
                doi = (ident.get("external-id-value") or "").strip()
                break

        works.append({
            "title": title,
            "year": int(year) if year and str(year).isdigit() else None,
            "type": (s.get("type") or "other").lower(),
            "venue": ((s.get("journal-title") or {}).get("value") or "").strip() or None,
            "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else None,
        })
    return works


def format_authors(authors):
    """Crossref author objects -> 'P. K. Donta, S. Dustdar', with me bolded."""
    out = []
    for a in authors:
        family = (a.get("family") or "").strip()
        given = (a.get("given") or "").strip()
        if not family:
            name = (a.get("name") or "").strip()
            if not name:
                continue
            out.append(name)
            continue
        initials = " ".join(f"{part[0]}." for part in given.split() if part)
        name = f"{initials} {family}".strip()
        if family.lower() == ME_FAMILY and given.lower().startswith(ME_GIVEN):
            name = f"<b>{name}</b>"
        out.append(name)
    if len(out) > 12:
        out = out[:12] + ["et al."]
    return ", ".join(out)


def fetch_datacite(doi, email):
    """arXiv and Zenodo DOIs are registered with DataCite, not Crossref."""
    url = "https://api.datacite.org/dois/" + urllib.parse.quote(doi, safe="")
    data = get_json(url, {"User-Agent": f"personal-website/1.0 (mailto:{email})"})
    time.sleep(0.12)
    if not data:
        return {}
    attrs = (data.get("data") or {}).get("attributes") or {}
    creators = []
    for c in attrs.get("creators") or []:
        creators.append({"given": c.get("givenName") or "",
                         "family": c.get("familyName") or "",
                         "name": c.get("name") or ""})
    venue = None
    if attrs.get("publisher"):
        pub = attrs["publisher"]
        venue = pub.get("name") if isinstance(pub, dict) else str(pub)
    return {
        "authors": format_authors(creators),
        "venue": venue,
        "year": attrs.get("publicationYear"),
        "cited": attrs.get("citationCount") or 0,
    }


def fetch_crossref(doi, cache, email):
    key = doi.lower()
    if key in cache:
        return cache[key]

    # arXiv / Zenodo prefixes are DataCite, asking Crossref returns nothing
    if key.startswith("10.48550") or key.startswith("10.5281"):
        rec = fetch_datacite(doi, email)
        cache[key] = rec
        return rec

    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    if email:
        url += "?mailto=" + urllib.parse.quote(email)
    data = get_json(url, {"User-Agent": f"personal-website/1.0 (mailto:{email})"})
    time.sleep(0.12)  # be a good citizen

    rec = {}
    if data and isinstance(data.get("message"), dict):
        m = data["message"]
        container = m.get("container-title") or []
        bits = []
        if m.get("volume"):
            bits.append(f"vol. {m['volume']}")
        if m.get("issue"):
            bits.append(f"no. {m['issue']}")
        if m.get("page"):
            bits.append(f"pp. {m['page']}")
        issued = ((m.get("issued") or {}).get("date-parts") or [[None]])[0]
        rec = {
            "authors": format_authors(m.get("author") or []),
            "venue": (container[0].strip() if container else None),
            "detail": ", ".join(bits) or None,
            "year": issued[0] if issued and issued[0] else None,
            "publisher": (m.get("publisher") or "").strip() or None,
            "cited": m.get("is-referenced-by-count") or 0,
        }

    cache[key] = rec
    return rec


def norm_title(s):
    """Loose title key, so 'Self-Healing: A Survey' == 'self healing a survey'."""
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def drop_duplicate_preprints(works):
    """A paper usually appears twice: once as an arXiv preprint, once as the
    published version. Keep the published one and discard the preprint."""
    published = {norm_title(w["title"]) for w in works
                 if w["type"] not in PREPRINT_TYPES}
    kept, dropped = [], 0
    for w in works:
        if w["type"] in PREPRINT_TYPES and norm_title(w["title"]) in published:
            dropped += 1
            continue
        kept.append(w)
    if dropped:
        print(f"  merged {dropped} preprint(s) into their published versions")
    return kept


def load_extras():
    """Manually-listed works (books in press, anything not yet in ORCID)."""
    path = ROOT / "_data" / "extra_publications.yml"
    if not path.exists():
        return []
    items = yaml.safe_load(path.read_text()) or []
    if isinstance(items, dict):
        items = items.get("items") or []
    out = []
    for it in items:
        if not it or not it.get("title"):
            continue
        out.append({
            "title": it["title"],
            "authors": it.get("authors"),
            "venue": it.get("venue"),
            "detail": it.get("detail"),
            "year": it.get("year") or 0,
            "url": it.get("url"),
            "type": (it.get("type") or "book").lower(),
            "doi": None,
        })
    if out:
        print(f"  {len(out)} manually-listed work(s) merged in")
    return out


def bucket(work_type):
    for name, types in GROUPS:
        if work_type in types:
            return name
    return GROUPS[-1][0]


def main():
    orcid = read_orcid_id()
    email = os.environ.get("CONTACT_EMAIL", "")
    print(f"Reading ORCID {orcid} …")

    works = fetch_orcid_works(orcid)
    print(f"  {len(works)} work groups")

    cache = load_cache()
    before = len(cache)

    for w in works:
        if not w["doi"]:
            continue
        cr = fetch_crossref(w["doi"], cache, email)
        if cr.get("authors"):
            w["authors"] = cr["authors"]
        if cr.get("venue"):
            w["venue"] = cr["venue"]
        if cr.get("detail"):
            w["detail"] = cr["detail"]
        if not w["year"] and cr.get("year"):
            w["year"] = cr["year"]
        if cr.get("cited"):
            w["cited"] = cr["cited"]

    save_cache(cache)
    print(f"  metadata: {len(cache) - before} new, {before} cached")

    works = drop_duplicate_preprints(works)
    works.extend(load_extras())

    # Drop anything with no year rather than sorting it to a random place.
    for w in works:
        if not w["year"]:
            w["year"] = 0

    grouped = {name: [] for name, _ in GROUPS}
    for w in works:
        entry = {k: w.get(k) for k in
                 ("title", "authors", "venue", "detail", "year", "url", "cited")}
        entry = {k: v for k, v in entry.items() if v}
        grouped[bucket(w["type"])].append(entry)

    out_groups = []
    for name, _ in GROUPS:
        items = sorted(grouped[name],
                       key=lambda e: (-(e.get("year") or 0), e.get("title", "")))
        if items:
            out_groups.append({"type": name, "items": items})

    everything = sorted(works, key=lambda w: -(w["year"] or 0))
    recent = []
    for w in everything[:10]:
        e = {k: w.get(k) for k in ("title", "authors", "venue", "detail", "year", "url", "cited")}
        recent.append({k: v for k, v in e.items() if v})

    payload = {
        "generated": time.strftime("%d %B %Y"),
        "source": f"https://orcid.org/{orcid}",
        "count": len(works),
        "recent": recent,
        "groups": out_groups,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        fh.write("# GENERATED FILE — do not edit by hand.\n")
        fh.write("# Rebuilt from ORCID by scripts/sync_orcid.py.\n")
        fh.write("# Fix mistakes in your ORCID record, not here.\n\n")
        yaml.safe_dump(payload, fh, allow_unicode=True, sort_keys=False, width=100)

    try:
        shown = OUT.relative_to(ROOT)
    except ValueError:
        shown = OUT
    print(f"Wrote {shown} — {len(works)} records "
          f"across {len(out_groups)} groups.")


if __name__ == "__main__":
    main()
