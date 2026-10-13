"""
Scrapes district.in's public Kolkata showtime pages for four tracked movies
and writes data.json for the static site (index.html fetches this directly,
no backend, no account needed). Designed to be run hourly by
.github/workflows/update.yml.

This only ever reads plain public pages (no login, no cookies, no auth
token) — see the project README for details on why that's the only
endpoint this script touches.
"""
import json, re, time, urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

MOVIES = [
    {"id": "230309", "name": "The Eken: Kerala-e Kurukshetra", "url": "https://www.district.in/movies/the-eken-kerala-e-kurukshetra-movie-tickets-in-kolkata-MV230309"},
    {"id": "213662", "name": "DeSu7", "url": "https://www.district.in/movies/desu7-movie-tickets-in-kolkata-MV213662"},
    {"id": "230211", "name": "Bohurupi: The Golden Daku", "url": "https://www.district.in/movies/bohurupi-the-golden-daku-movie-tickets-in-kolkata-MV230211"},
    {"id": "220611", "name": "Emperor vs Sarat Chandra", "url": "https://www.district.in/movies/emperor-vs-sarat-chandra-movie-tickets-in-kolkata-MV220611"},
]

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"


def fetch_next_data(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", errors="replace")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("NEXT_DATA not found for " + url)
    return json.loads(m.group(1))


def extract(next_data):
    ms = next_data["props"]["pageProps"]["data"]["serverState"]["movieSessions"]
    key = next(iter(ms))
    node = ms[key]
    show_dates = (node.get("data") or {}).get("sessionDates", [])
    arranged = node.get("arrangedSessions", [])
    by_cinema = {}
    for cinema in arranged:
        cname = cinema.get("entityName")
        shows = by_cinema.setdefault(cname, [])
        for sess in cinema.get("sessions", []):
            total = sess.get("total", 0)
            avail = sess.get("avail", 0)
            filled = total - avail
            fill_rate = round(filled / total * 100, 1) if total else None
            revenue = 0
            for area in sess.get("areas", []) or []:
                a_total = area.get("sTotal") or 0
                a_avail = area.get("sAvail") or 0
                a_price = area.get("price") or 0
                revenue += max(a_total - a_avail, 0) * a_price
            show_time = sess.get("showTime", "")
            # District's showTime is UTC with no suffix (verified: 03:50 there == 09:20 AM IST on the page).
            if show_time:
                utc_dt = datetime.strptime(show_time, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                ist_dt = utc_dt.astimezone(IST)
                date = ist_dt.strftime("%Y-%m-%d")
                time_part = ist_dt.strftime("%H:%M")
            else:
                date, time_part = "", ""
            shows.append({
                "date": date,
                "time": time_part,
                "audi": sess.get("audi"),
                "fmt": sess.get("scrnFmt"),
                "tag": sess.get("premiumLabel"),
                "total": total,
                "avail": avail,
                "filled": filled,
                "fillRate": fill_rate,
                "status": sess.get("seatStatus"),
                "revenue": revenue,
            })
    return show_dates, by_cinema


def scrape_movie(m):
    nd = fetch_next_data(m["url"])
    show_dates, by_cinema = extract(nd)
    seen_dates = set()
    for shows in by_cinema.values():
        for s in shows:
            seen_dates.add(s["date"])
    for d in show_dates:
        if d in seen_dates:
            continue
        time.sleep(1)
        try:
            nd2 = fetch_next_data(m["url"] + "?fromdate=" + d)
            _, by_cinema2 = extract(nd2)
            for cname, shows2 in by_cinema2.items():
                by_cinema.setdefault(cname, []).extend(shows2)
            seen_dates.add(d)
        except Exception as e:
            print("  ! failed date", d, "for", m["name"], e)
    cinemas = [{"name": cname, "shows": shows} for cname, shows in by_cinema.items() if shows]
    return {
        "id": m["id"],
        "name": m["name"],
        "url": m["url"],
        "showDates": show_dates,
        "scrapedAt": datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "cinemas": cinemas,
    }


def main():
    out_path = "data.json"
    previous = {}
    try:
        with open(out_path) as f:
            prev_payload = json.load(f)
        previous = {m["id"]: m for m in prev_payload.get("movies", [])}
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    movies = []
    for m in MOVIES:
        try:
            data = scrape_movie(m)
            total_shows = sum(len(c["shows"]) for c in data["cinemas"])
            print(f"{m['name']}: {total_shows} shows, {len(data['cinemas'])} cinemas")
            movies.append(data)
        except Exception as e:
            # Keep last-known-good data for this movie rather than wiping it out
            # on a transient failure (network blip, page layout hiccup, etc.).
            print(f"  ! failed to scrape {m['name']}: {e} — keeping previous snapshot if any")
            if m["id"] in previous:
                movies.append(previous[m["id"]])
        time.sleep(1)

    payload = {
        "generatedAt": datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "movies": movies,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"Wrote {out_path} ({len(json.dumps(payload))} bytes)")


if __name__ == "__main__":
    main()
