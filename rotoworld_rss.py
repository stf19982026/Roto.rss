#!/usr/bin/env python3
"""
Rotoworld NBA Player News -> feed RSS

Scarica https://www.nbcsports.com/fantasy/basketball/player-news,
estrae le news (giocatore, titolo, commento, categoria, fonte) e genera:
  - docs/feed.xml        -> tutte le news NBA
  - docs/feed-miei.xml   -> solo i giocatori elencati in players.txt (se esiste)

Le news già viste vengono conservate in docs/news.json, così il feed
mantiene lo storico (ultime MAX_ITEMS) anche quando la pagina mostra solo le ultime 10.
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup, NavigableString

URL = "https://www.nbcsports.com/fantasy/basketball/player-news"
BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "docs"
STORE = OUT_DIR / "news.json"
PLAYERS_FILE = BASE / "players.txt"
MAX_ITEMS = 150
CATEGORIES = {"Injury", "Recap", "Transaction", "Headline"}
PLAYER_HREF = re.compile(r"/nba/[^/]+/[^/?#]+/?$")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


TEAM_RE = re.compile(
    r"\b([A-Z]{2,4})\s+(?:Point Guard|Shooting Guard|Small Forward|Power Forward|"
    r"Guard|Forward|Center|Head Coach|Coach|General Manager|Owner)"
)
STOP_RE = re.compile(r"^(Source:|More .+ News$|Link copied|Personalize your)")


def strings_between(start, stop_names=("h2", "h3")):
    """Testi (in ordine) dopo `start` fino al prossimo h2/h3."""
    out = []
    for el in start.next_elements:
        if getattr(el, "name", None) in stop_names:
            break
        if type(el) is NavigableString and start not in el.parents:
            t = clean(el)
            if t and el.parent.name not in ("script", "style", "noscript"):
                out.append((t, el))
    return out


def parse(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for h3 in soup.find_all("h3"):
        headline = clean(h3.get_text(" "))
        if len(headline) < 25:
            continue

        # giocatore = l'h2 più vicino PRIMA del titolo
        h2 = h3.find_previous("h2")
        a_player = h2.find("a", href=True) if h2 else None
        if not a_player or "/nba/" not in a_player["href"]:
            continue
        player = clean(a_player.get_text(" "))
        player_url = a_player["href"]
        if player_url.startswith("/"):
            player_url = "https://www.nbcsports.com" + player_url

        # squadra: testo tra nome e titolo, es. "POR Center #9"
        team = ""
        m = TEAM_RE.search(" ".join(t for t, _ in strings_between(h2)))
        if m:
            team = m.group(1)

        # commento, categoria e fonte: testi dopo il titolo, in ordine
        body_parts, category, source = [], "", ""
        after = strings_between(h3)
        for i, (t, node) in enumerate(after):
            if t in CATEGORIES:
                category = t
                continue
            if t.startswith("Source:"):
                rest = t[len("Source:"):].strip()
                source = rest or (after[i + 1][0] if i + 1 < len(after) else "")
                break
            if STOP_RE.match(t):
                break
            if not category:  # il commento sta prima della categoria
                body_parts.append(t)
        body = clean(" ".join(body_parts))
        author = ""
        m = re.search(r"\s[-–]\s*([A-Z][\w.'’ -]+)$", body)
        if m:
            author = m.group(1).strip()
            body = body[: m.start()].strip()

        guid = hashlib.sha1(f"{player}|{headline}".encode()).hexdigest()[:16]
        items.append(
            {
                "id": guid,
                "player": player,
                "team": team,
                "headline": headline,
                "body": body,
                "author": author,
                "category": category,
                "source": source,
                "link": player_url.rstrip("/") + "/news",
            }
        )
    # dedup mantenendo l'ordine
    seen, out = set(), []
    for it in items:
        if it["id"] not in seen:
            seen.add(it["id"])
            out.append(it)
    return out


def load_store():
    if STORE.exists():
        return json.loads(STORE.read_text(encoding="utf-8"))
    return []


def merge(old, new):
    now = format_datetime(datetime.now(timezone.utc))
    known = {it["id"] for it in old}
    fresh = []
    for it in new:
        if it["id"] not in known:
            it["pubDate"] = now
            fresh.append(it)
    return (fresh + old)[:MAX_ITEMS], len(fresh)


def build_rss(items, title, self_name):
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        f"<title>{escape(title)}</title>",
        f"<link>{URL}</link>",
        "<description>Rotoworld NBA player news (feed non ufficiale)</description>",
        "<ttl>10</ttl>",
    ]
    for it in items:
        tag = f"[{it['category']}] " if it.get("category") else ""
        team = f" ({it['team']})" if it.get("team") else ""
        desc = f"<p><b>{escape(it['headline'])}</b></p><p>{escape(it['body'])}</p>"
        if it.get("author"):
            desc += f"<p><i>{escape(it['author'])}</i></p>"
        if it.get("source"):
            desc += f"<p>Fonte: {escape(it['source'])}</p>"
        parts += [
            "<item>",
            f"<title>{escape(tag + it['player'] + team + ': ' + it['headline'])}</title>",
            f"<link>{escape(it['link'])}</link>",
            f'<guid isPermaLink="false">{it["id"]}</guid>',
            f"<pubDate>{it['pubDate']}</pubDate>",
            f"<category>{escape(it.get('category') or 'News')}</category>",
            f"<description><![CDATA[{desc}]]></description>",
            "</item>",
        ]
    parts.append("</channel></rss>")
    return "\n".join(parts)


def load_players():
    if not PLAYERS_FILE.exists():
        return []
    return [
        l.strip().lower()
        for l in PLAYERS_FILE.read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.startswith("#")
    ]


def main(html_file=None):
    if html_file:
        html = Path(html_file).read_text(encoding="utf-8")
    else:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        html = r.text

    # copia della pagina (una volta sola) per diagnosi se la struttura cambia
    OUT_DIR.mkdir(exist_ok=True)
    dbg = OUT_DIR / "page.html"
    if not html_file and not dbg.exists():
        dbg.write_text(html, encoding="utf-8")

    new = parse(html)
    if not new:
        print("ATTENZIONE: nessuna news trovata (struttura pagina cambiata?)")
        sys.exit(1)

    OUT_DIR.mkdir(exist_ok=True)
    items, n_new = merge(load_store(), new)
    STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "feed.xml").write_text(
        build_rss(items, "Rotoworld NBA Player News", "feed.xml"), encoding="utf-8"
    )

    players = load_players()
    if players:
        mine = [it for it in items if any(p in it["player"].lower() for p in players)]
        (OUT_DIR / "feed-miei.xml").write_text(
            build_rss(mine, "Rotoworld NBA – I miei giocatori", "feed-miei.xml"),
            encoding="utf-8",
        )
    print(f"News sulla pagina: {len(new)} | nuove: {n_new} | nel feed: {len(items)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
