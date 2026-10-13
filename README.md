# Pujo Movies 2026

Public, no-login box-office tracker for four Kolkata Pujo-season releases —
**The Eken: Kerala-e Kurukshetra**, **DeSu7**, **Bohurupi: The Golden Daku**,
and **Emperor vs Sarat Chandra** — covering fill rate, estimated revenue,
trends, and head-to-head comparisons across every cinema in Kolkata.

This is a static mirror of a live Claude Artifact, built specifically so it
can be opened by anyone with the link, no Claude account required.

## How it works

- `scrape_and_generate.py` fetches the public (no login, no auth token)
  showtime pages on district.in for each movie, extracts the embedded
  `__NEXT_DATA__` JSON, computes per-show fill rate and an estimated revenue
  (booked seats × the listed ticket price per seat category), and writes the
  result to `data.json`.
- `.github/workflows/update.yml` runs that script on a schedule (roughly
  every 30 minutes) via GitHub Actions and commits the refreshed `data.json`
  — no server, no database, nothing else to maintain.
- `bms_halls.json` is a separate, hand-maintained file: showtimes for cinemas
  that only list on BookMyShow (not District), checked manually since
  BookMyShow sits behind bot-detection that this project won't try to
  automate around. The GitHub Action never touches this file — update it by
  hand when you re-check BookMyShow. It carries a status band per show
  (Available / Filling Fast / Housefull), not an exact seat count, so it has
  no fill % or revenue — the page renders it as a visually distinct
  "BookMyShow — other halls" section and never mixes it into the District
  numbers.
- `index.html` is a static page that fetches `data.json` (and `bms_halls.json`
  if present) directly and renders the dashboard client-side. No backend.
- GitHub Pages serves `index.html` straight from this repo.

## Data notes

- **Fill rate** = booked seats ÷ total seats per showtime, aggregated across
  price tiers.
- **Estimated revenue** = booked seats × the ticket price listed for that
  seat category on district.in, summed per show. It excludes convenience
  fees, taxes, and any offline/box-office sales — treat it as a directional
  gross, not an official number.
- **Cinema chain** (in the head-to-head tab) is inferred from the venue
  name's prefix on district.in, not an official affiliation list.
- The scraper only ever fetches plain public pages — the same ones a human
  visitor gets — with a polite 1-second delay between requests. It never
  logs in, solves a CAPTCHA, or calls an authenticated endpoint.

## Running it yourself

```bash
python3 scrape_and_generate.py   # writes data.json
python3 -m http.server 8080      # then open http://localhost:8080
```
