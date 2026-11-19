#!/usr/bin/env python3
"""Build every page of srigokulkrishnan.com from the JSON in _build/content.

    python3 _build/build.py

Words live in _build/content (site.json, projects/*.json, posts/*.json); layout and
components live here; styles in assets/site/site.css. Output is plain HTML in the repo
root, so the site stays static and Netlify serves it as-is.
"""
from __future__ import annotations

import html
import json
import math
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
CONTENT = Path(__file__).resolve().parent / "content"
ORIGIN = "https://www.srigokulkrishnan.com"

try:
    from PIL import Image  # optional: only used for width/height attributes
except ImportError:  # pragma: no cover
    Image = None

SITE = json.loads((CONTENT / "site.json").read_text())
PROJECTS = [p for p in SITE["projects"]]
CASE = {p["slug"]: json.loads((CONTENT / "projects" / f"{p['slug']}.json").read_text())
        for p in PROJECTS if p.get("slug")}
POSTS = []
for f in sorted((CONTENT / "posts").glob("*.json")):
    d = json.loads(f.read_text())
    d["slug"] = f.stem
    d["file"] = "blog-post.html" if f.stem == "ux-is-a-process" else f"post-{f.stem}.html"
    POSTS.append(d)
POSTS.sort(key=lambda p: p["date"], reverse=True)

MISSING: list[str] = []
e = html.escape


# ---------------------------------------------------------------- helpers
def url(path: str) -> str:
    """Encode a ./relative asset path (several files have spaces in their names)."""
    if path.startswith(("http://", "https://", "mailto:", "#")):
        return path
    return quote(path, safe="/.:-_~()")


def dims(path: str) -> str:
    p = ROOT / path.lstrip("./")
    if not p.exists():
        MISSING.append(path)
        return ""
    if Image is None or p.suffix.lower() in (".webm", ".mp4", ".svg"):
        return ""
    try:
        with Image.open(p) as im:
            return f' width="{im.width}" height="{im.height}"'
    except Exception:
        return ""


THUMBS = ROOT / "assets" / "site" / "img"


def thumb(path: str, width: int) -> str:
    """A resized WebP copy of an image for display (originals stay for the lightbox)."""
    src = ROOT / path.lstrip("./")
    if Image is None or not src.exists() or src.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        return path
    name = re.sub(r"[^a-z0-9]+", "-", path.lstrip("./").lower().rsplit(".", 1)[0]).strip("-") + f"-{width}.webp"
    out = THUMBS / name
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        THUMBS.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
            if im.width > width:
                im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            im.save(out, "WEBP", quality=82, method=6)
    return f"./assets/site/img/{name}"


def img(path: str, alt: str = "", cls: str = "", eager: bool = False, width: int = 0) -> str:
    c = f' class="{cls}"' if cls else ""
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    shown = thumb(path, width) if width else path
    return f'<img src="{e(url(shown))}" alt="{e(alt)}"{dims(shown)}{c} {load}>'


def fmt_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def words(obj) -> int:
    if isinstance(obj, str):
        return len(obj.split())
    if isinstance(obj, list):
        return sum(words(x) for x in obj)
    if isinstance(obj, dict):
        return sum(words(v) for k, v in obj.items() if k not in ("img", "video", "cover", "date", "src"))
    return 0


ARROW = '<span class="arrow" aria-hidden="true">↗</span>'
ICON = {
    "sun": '<svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    "moon": '<svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 8h16M4 16h16"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
}


# ---------------------------------------------------------------- layout
NAV = [("Work", "work.html"), ("About", "aboutme.html"), ("Writing", "blog.html")]


def layout(title: str, description: str, body: str, current: str = "", image: str = "") -> str:
    full = title if title == SITE["name"] else f"{title} · {SITE['name']}"
    og_img = f'\n  <meta property="og:image" content="{ORIGIN}/{e(url(image.lstrip("./")))}">' if image else ""
    nav = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if href == current else ""}>{label}</a>' for label, href in NAV
    )
    email = SITE["email"]
    socials = "".join(f'<li><a href="{u}" rel="me noopener" target="_blank">{n}</a></li>' for n, u in SITE["social"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(full)}</title>
  <meta name="description" content="{e(description)}">
  <meta name="author" content="{e(SITE['name'])}">
  <meta name="theme-color" content="#fafaf7" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0e0e0d" media="(prefers-color-scheme: dark)">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{e(full)}">
  <meta property="og:description" content="{e(description)}">{og_img}
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="./assets/img/favicon.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Inter+Tight:wght@500;600;700&family=Instrument+Serif:ital@0;1&display=swap">
  <link rel="stylesheet" href="./assets/site/site.css">
  <script>
    document.documentElement.classList.add('js');
    try {{ var t = localStorage.getItem('theme'); if (t) document.documentElement.dataset.theme = t; }} catch (e) {{}}
  </script>
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="wrap">
      <a class="wordmark" href="./index.html" aria-label="{e(SITE['name'])}, home"><span class="dot" aria-hidden="true"></span>{e(SITE['name'])}</a>
      <nav class="nav" id="nav" aria-label="Main">{nav}<a href="mailto:{email}">Contact</a></nav>
      <div class="header-actions">
        <button class="icon-btn theme-toggle" type="button" aria-label="Switch light or dark theme">{ICON['sun']}{ICON['moon']}</button>
        <button class="icon-btn menu-btn" type="button" aria-label="Menu" aria-controls="nav" aria-expanded="false">{ICON['menu']}</button>
      </div>
    </div>
  </header>
  <main id="main">
{body}
  </main>
  <footer class="site-footer">
    <div class="wrap">
      <div class="footer-grid">
        <div>
          <p class="footer-big">Have an interesting, stupid or crazy idea you'd like some help building?</p>
          <a class="btn" href="mailto:{email}">Let's talk {ARROW}</a>
        </div>
        <div>
          <h3>Pages</h3>
          <ul><li><a href="./index.html">Home</a></li>{''.join(f'<li><a href="./{h}">{l}</a></li>' for l, h in NAV)}</ul>
        </div>
        <div>
          <h3>Elsewhere</h3>
          <ul>{socials}<li><a href="mailto:{email}">Email</a></li></ul>
        </div>
      </div>
      <div class="footer-base"><span>© <span data-year>{date.today().year}</span> {e(SITE['name'])}</span><span>Built with ❤️ from India.</span></div>
    </div>
  </footer>
  <dialog class="lightbox" aria-label="Image preview">
    <button class="icon-btn" type="button" aria-label="Close">{ICON['close']}</button>
    <img src="" alt=""><p></p>
  </dialog>
  <script src="./assets/site/site.js" defer></script>
</body>
</html>
"""


def write(name: str, page: str) -> None:
    (ROOT / name).write_text(page)
    print("  wrote", name)


# ---------------------------------------------------------------- shared pieces
def project_href(p: dict) -> str:
    return f"./{p['slug']}.html" if p.get("slug") else p["url"]


def card(p: dict, feature: bool = False, filterable: bool = False) -> str:
    ext = not p.get("slug")
    target = ' target="_blank" rel="noopener"' if ext else ""
    tags = f' data-tags="{e("|".join(p["tags"]))}"' if filterable else ""
    cls = "card card--feature" if feature else "card"
    return f"""<a class="{cls} reveal" href="{e(url(project_href(p)))}"{target}{tags}>
  <div class="card-media">{img(p['card'], p['title'], width=1200)}</div>
  <div class="card-body">
    <span class="card-kind">{e(p['kind'])}</span>
    <span class="card-title">{e(p['title'])}{ARROW}</span>
    <p class="card-summary">{e(p['summary'])}</p>
  </div>
</a>"""


def quotes_block() -> str:
    items = "".join(
        f"""<figure class="quote"><blockquote>{e(q)}</blockquote>
<figcaption>{img(a, n, width=120)}<div><strong>{e(n)}</strong><span>{e(r)}</span></div></figcaption></figure>"""
        for q, n, r, a in SITE["testimonials"]
    )
    return f"""<section class="section" aria-labelledby="kind-words">
  <div class="wrap">
    <div class="section-head reveal"><div><span class="kicker"><span class="dot"></span>Kind words</span><h2 id="kind-words" style="margin-top:14px">What people say about working with me</h2></div></div>
    <div class="quotes reveal" tabindex="0" aria-label="Testimonials, scroll sideways">{items}</div>
  </div>
</section>"""


def experience_rows() -> str:
    out = []
    for name, text, link in SITE["experience"]:
        if link:
            ext = link.startswith("http")
            t = ' target="_blank" rel="noopener"' if ext else ""
            out.append(f'<a class="row reveal" href="{e(link)}"{t}><span class="row-name">{e(name)}</span><p class="row-text">{e(text)}</p>{ARROW}</a>')
        else:
            out.append(f'<div class="row reveal"><span class="row-name">{e(name)}</span><p class="row-text">{e(text)}</p><span></span></div>')
    return f'<div class="rows">{"".join(out)}</div>'


def post_rows(posts) -> str:
    return '<div class="post-list">' + "".join(
        f"""<a class="post-row reveal" href="./{p['file']}">
  <div class="thumb">{img(p['cover'], '', width=800)}</div>
  <div><div class="post-meta"><time datetime="{p['date']}">{fmt_date(p['date'])}</time><span class="sep"></span><span>{max(1, math.ceil(words(p['sections']) / 220))} min read</span></div>
  <h3>{e(p['title'])}</h3><p>{e(p['summary'])}</p></div>
</a>""" for p in posts) + "</div>"


def cta() -> str:
    return f"""<section class="section"><div class="wrap"><div class="cta reveal">
  <span class="kicker" style="color:inherit;opacity:.7"><span class="dot"></span>Let's work together</span>
  <h2>Have an interesting, stupid or crazy idea you'd like some help building?</h2>
  <div class="btns"><a class="btn" href="mailto:{SITE['email']}">{e(SITE['email'])} {ARROW}</a><a class="btn btn--ghost" href="./aboutme.html">More about me</a></div>
</div></div></section>"""


# ---------------------------------------------------------------- content blocks
def figure(src: str, caption: str = "", alt: str = "") -> str:
    cap = f"<figcaption>{e(caption)}</figcaption>" if caption else ""
    return f'<figure class="figure"><button class="frame" type="button" data-zoom="{e(url(src))}" aria-label="Enlarge image">{img(src, alt or caption, width=1600)}</button>{cap}</figure>'


def blocks(body: list, layout_hint: str = "") -> str:
    out, i = [], 0
    if layout_hint == "gallery":
        figs = "".join(figure(b["img"], b.get("caption", "")) for b in body if "img" in b)
        return f'<div class="masonry">{figs}</div>'
    while i < len(body):
        b = body[i]
        if "img" in b:
            run = []
            while i < len(body) and "img" in body[i]:
                run.append(body[i]); i += 1
            if len(run) == 1:
                out.append(figure(run[0]["img"], run[0].get("caption", "")))
            else:
                cols = " gallery--3" if len(run) % 3 == 0 and len(run) > 2 else ""
                out.append(f'<div class="gallery gallery--natural{cols}">' + "".join(figure(r["img"], r.get("caption", "")) for r in run) + "</div>")
            continue
        if "p" in b:
            out.append(f"<p>{e(b['p'])}</p>")
        elif "sub" in b:
            out.append(f"<h3>{e(b['sub'])}</h3>")
        elif "list" in b:
            items = []
            for li in b["list"]:
                m = re.match(r"^([^:]{2,48}):\s+(.+)$", li)
                items.append(f"<li><strong>{e(m.group(1))}:</strong> {e(m.group(2))}</li>" if m else f"<li>{e(li)}</li>")
            out.append("<ul>" + "".join(items) + "</ul>")
        elif "quote" in b:
            out.append(f"<blockquote>{e(b['quote'])}</blockquote>")
        elif "video" in b:
            out.append(f'<div class="case-cover"><video src="{e(url(b["video"]))}" autoplay muted loop playsinline></video></div>')
        elif "gallery" in b:
            out.append('<div class="gallery">' + "".join(figure(g["img"], g.get("caption", "")) for g in b["gallery"]) + "</div>")
        elif "swatches" in b:
            out.append('<div class="swatches">' + "".join(
                f'<div class="swatch"><i style="background:{e(h)}"></i><div>{e(n)}<br><code>{e(h.upper())}</code></div></div>'
                for n, h in b["swatches"]) + "</div>")
        elif "steps" in b:
            out.append('<div class="steps">' + "".join(f'<div class="step"><strong>{e(t)}</strong><span>{e(d)}</span></div>' for t, d in b["steps"]) + "</div>")
        elif "pairs" in b:
            wide = " pairs--wide" if any(len(d) > 40 for _, d in b["pairs"]) else ""
            out.append(f'<div class="pairs{wide}">' + "".join(f"<div><strong>{e(t)}</strong><span>{e(d)}</span></div>" for t, d in b["pairs"]) + "</div>")
        i += 1
    return "\n".join(out)


def experiment(exp) -> str:
    name, text, link, pic = exp
    inner = (f'<div><span class="kicker"><span class="dot"></span>Experiments</span><h3 id="experiments">{e(name)}</h3>'
             f'<p class="lead">{e(text)}</p>'
             + (f'<span class="btn btn--ghost">Visit {e(link.split("//")[-1].removeprefix("www."))} {ARROW}</span>' if link else "")
             + f'</div>{img(pic, name, width=1200)}')
    if link:
        return f'<a class="experiment reveal" href="{e(link)}" target="_blank" rel="noopener">{inner}</a>'
    return f'<div class="experiment reveal">{inner}</div>'


# ---------------------------------------------------------------- pages
def build_index() -> None:
    h = SITE["hero"]
    featured = [p for p in PROJECTS if p.get("slug") in ("stayonmap", "happenous")]
    rest = [p for p in PROJECTS if p not in featured][:6]
    title = e(h["title"]).replace("trust", '<span class="serif">trust</span>')
    logos = "".join(img(src, name) for name, src in SITE["clients"])
    services = "".join(
        f'<div class="tile reveal"><span class="num">0{i}</span><h3>{e(n)}</h3><p>{e(d)}</p></div>'
        for i, (n, d) in enumerate(SITE["services"], 1))
    exp = SITE["experiments"][0]
    body = f"""<section class="hero"><div class="wrap hero-grid">
  <div>
    <span class="kicker reveal"><span class="dot"></span>{e(h['kicker'])}</span>
    <h1 class="reveal">{title}</h1>
    <p class="lead reveal">{e(h['lead'])}</p>
    <div class="btns reveal"><a class="btn" href="./work.html">See my work {ARROW}</a><a class="btn btn--ghost" href="mailto:{SITE['email']}">Get in touch</a></div>
  </div>
  {img(SITE['about']['photo'], SITE['name'], 'hero-photo reveal', eager=True, width=600)}
</div></section>
<section class="logos" aria-label="Companies I've worked with"><div class="wrap"><span>Companies I've worked with</span>{logos}</div></section>

<section class="section" id="work" aria-labelledby="selected-work">
  <div class="wrap">
    <div class="section-head reveal"><div><span class="kicker"><span class="dot"></span>Selected work</span><h2 id="selected-work" style="margin-top:14px">Products I'm building right now</h2></div>
    <a class="btn btn--ghost" href="./work.html">All projects {ARROW}</a></div>
    <div class="grid grid--2">{''.join(card(p, feature=True) for p in featured)}</div>
  </div>
</section>
<section class="section" aria-labelledby="more-work">
  <div class="wrap">
    <div class="section-head reveal"><h2 id="more-work">Brand, web and case studies</h2></div>
    <div class="grid grid--3">{''.join(card(p) for p in rest)}</div>
  </div>
</section>

<section class="section" aria-labelledby="what-i-do">
  <div class="wrap">
    <div class="section-head reveal"><div><span class="kicker"><span class="dot"></span>What I do</span><h2 id="what-i-do" style="margin-top:14px">From the first sketch to the shipped app</h2></div></div>
    <div class="tiles">{services}</div>
  </div>
</section>

<section class="section" aria-labelledby="experience">
  <div class="wrap">
    <div class="section-head reveal"><div><span class="kicker"><span class="dot"></span>Experience</span><h2 id="experience" style="margin-top:14px">Where I've been building</h2></div></div>
    {experience_rows()}
  </div>
</section>

{quotes_block()}

<section class="section" aria-labelledby="experiments">
  <div class="wrap">
    {experiment(exp)}
  </div>
</section>

<section class="section" aria-labelledby="writing">
  <div class="wrap">
    <div class="section-head reveal"><div><span class="kicker"><span class="dot"></span>Writing</span><h2 id="writing" style="margin-top:14px">Notes on design</h2></div>
    <a class="btn btn--ghost" href="./blog.html">All writing {ARROW}</a></div>
    {post_rows(POSTS[:3])}
  </div>
</section>
{cta()}"""
    write("index.html", layout(SITE["name"], f"{SITE['name']} is a product designer in India, building StayOnMap and Happenous, and designing brands, websites and apps people can trust.", body, "", "./assets/img/stayonmap/card-map.jpg"))


def build_work() -> None:
    tags = []
    for p in PROJECTS:
        for t in p["tags"]:
            if t not in tags:
                tags.append(t)
    chips = '<button class="chip" type="button" data-filter="all" aria-pressed="true">All</button>' + "".join(
        f'<button class="chip" type="button" data-filter="{e(t)}" aria-pressed="false">{e(t)}</button>' for t in tags)
    body = f"""<section class="hero"><div class="wrap">
  <span class="kicker reveal"><span class="dot"></span>Work</span>
  <h1 class="reveal">Products, brands and <span class="serif">case studies</span>.</h1>
  <p class="lead reveal">Check out some of my projects with creative ideas and great design: two live products, brand and web work for clients, and design sprints that show how I think.</p>
</div></section>
<section class="section" style="padding-top:0"><div class="wrap">
  <div class="filters" role="group" aria-label="Filter projects">{chips}</div>
  <div class="grid grid--2">{''.join(card(p, filterable=True) for p in PROJECTS)}</div>
</div></section>
{cta()}"""
    write("work.html", layout("Work", "Selected projects by Sri Gokul Krishnan: StayOnMap, Happenous, Cosmonus, brand identities, websites and UX case studies.", body, "work.html", "./assets/img/stayonmap/card-map.jpg"))


def build_about() -> None:
    a = SITE["about"]
    process = "".join(
        f'<div class="tile reveal"><span class="num">0{i}</span><h3>{e(n)}</h3><p>{e(d)}</p></div>'
        for i, (n, d) in enumerate(SITE["process"], 1))
    services = "".join(
        f'<div class="row reveal"><span class="row-name">{e(n)}</span><p class="row-text">{e(d)}</p><span></span></div>'
        for n, d in SITE["services"])
    socials = "".join(f'<li><a href="{u}" rel="me noopener" target="_blank">{n}</a></li>' for n, u in SITE["social"])
    body = f"""<section class="hero"><div class="wrap">
  <span class="kicker reveal"><span class="dot"></span>About</span>
  <h1 class="reveal">A little bit <span class="serif">about myself</span>.</h1>
</div></section>
<section class="section" style="padding-top:0"><div class="wrap about-grid">
  <div class="prose reveal">{''.join(f'<p>{e(p)}</p>' for p in a['intro'])}
    <h3>Get in touch</h3>
    <p>If you want to work with me, feel free to reach out at <a href="mailto:{SITE['email']}">{e(SITE['email'])}</a>.</p>
    <ul class="contact-list"><li><a href="mailto:{SITE['email']}">{e(SITE['email'])}</a></li><li><a href="tel:{SITE['phone'].replace(' ', '')}">{e(SITE['phone'])}</a></li>{socials}</ul>
  </div>
  <div class="about-photo reveal">{img(a['photo'], SITE['name'], eager=True, width=900)}</div>
</div></section>

<section class="section" aria-labelledby="process">
  <div class="wrap">
    <div class="section-head reveal"><div><span class="kicker"><span class="dot"></span>My design process</span><h2 id="process" style="margin-top:14px">A user-centred dance between understanding and invention</h2></div></div>
    <div class="tiles">{process}</div>
  </div>
</section>

<section class="section" aria-labelledby="services">
  <div class="wrap">
    <div class="section-head reveal"><div><span class="kicker"><span class="dot"></span>What I do</span><h2 id="services" style="margin-top:14px">Services</h2></div></div>
    <div class="rows">{services}</div>
  </div>
</section>

<section class="section" aria-labelledby="experience">
  <div class="wrap">
    <div class="section-head reveal"><div><span class="kicker"><span class="dot"></span>Experience</span><h2 id="experience" style="margin-top:14px">Where I've been building</h2></div></div>
    {experience_rows()}
  </div>
</section>
{quotes_block()}
{cta()}"""
    write("aboutme.html", layout("About", f"About {SITE['name']}: product designer, builder of StayOnMap and Happenous, and founder of the AstusX design studio.", body, "aboutme.html", a["photo"]))


def build_project(i: int, p: dict) -> None:
    d = CASE[p["slug"]]
    meta = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in d.get("meta", []))
    links = []
    for ln in d.get("links", []):
        label, href = (ln if isinstance(ln, list) else ["View prototype", ln])
        links.append(f'<a class="btn{" btn--ghost" if links else ""}" href="{e(href)}" target="_blank" rel="noopener">{e(label)} {ARROW}</a>')
    hero = d.get("hero") or p["card"]
    if hero.endswith((".webm", ".mp4")):
        cover = f'<video src="{e(url(hero))}" autoplay muted loop playsinline></video>'
    else:
        cover = img(hero, p["title"], eager=True, width=2000)
    sections = []
    for n, s in enumerate(d["sections"], 1):
        sections.append(f"""<section class="case-section">
  <h2 class="reveal"><span class="num">{n:02d}</span>{e(s['heading'])}</h2>
  <div class="prose reveal">{blocks(s['body'], s.get('layout', ''))}</div>
</section>""")
    slugs = [x for x in PROJECTS if x.get("slug")]
    nxt = slugs[(slugs.index(p) + 1) % len(slugs)]
    body = f"""<article>
<header class="case-hero"><div class="wrap">
  <a class="crumb reveal" href="./work.html">← All work</a>
  <h1 class="reveal">{e(d['title'])}</h1>
  <p class="tagline reveal">{e(d.get('tagline') or p['summary'])}</p>
  <dl class="meta reveal">{meta}</dl>
  {f'<div class="btns reveal">{"".join(links)}</div>' if links else ''}
</div></header>
<div class="wrap"><div class="case-cover reveal">{cover}</div></div>
<div class="wrap">{''.join(sections)}</div>
</article>
<div class="wrap"><a class="next-project reveal" href="./{nxt['slug']}.html"><span class="kicker"><span class="dot"></span>Next project</span><span class="big">{e(nxt['title'])} →</span></a></div>"""
    write(f"{p['slug']}.html", layout(p["title"], f"{p['title']}: {p['summary']}", body, "work.html", p["card"]))


def build_blog() -> None:
    body = f"""<section class="hero"><div class="wrap">
  <span class="kicker reveal"><span class="dot"></span>Writing</span>
  <h1 class="reveal">Design diaries: navigating the <span class="serif">creative landscape</span>.</h1>
  <p class="lead reveal">Notes on product design, design systems and what I learn building StayOnMap and Happenous.</p>
</div></section>
<section class="section" style="padding-top:0"><div class="wrap">{post_rows(POSTS)}</div></section>
<section class="section"><div class="wrap">
  <a class="row reveal" href="https://www.cosmonus.com" target="_blank" rel="noopener"><span class="row-name">More at Cosmonus</span><p class="row-text">Research notes and plain-language explainers from the team behind StayOnMap and Happenous.</p>{ARROW}</a>
</div></section>
{cta()}"""
    write("blog.html", layout("Writing", f"Writing by {SITE['name']} on product design, design systems and building StayOnMap and Happenous.", body, "blog.html", POSTS[0]["cover"]))


def build_post(p: dict) -> None:
    secs = []
    for s in p["sections"]:
        head = f"<h2>{e(s['heading'])}</h2>" if s["heading"] else ""
        secs.append(head + blocks(s["body"]))
    others = [x for x in POSTS if x is not p][:2]
    tags = "".join(f'<span class="tag">{e(t)}</span>' for t in p.get("tags", []))
    body = f"""<article>
<header class="article-head"><div class="wrap narrow" style="margin-inline:auto">
  <a class="crumb reveal" href="./blog.html">← All writing</a>
  <h1 class="reveal">{e(p['title'])}</h1>
  <p class="lead reveal">{e(p['summary'])}</p>
  <div class="post-meta reveal"><span>{e(SITE['name'])}</span><span class="sep"></span><time datetime="{p['date']}">{fmt_date(p['date'])}</time><span class="sep"></span><span>{max(1, math.ceil(words(p['sections']) / 220))} min read</span></div>
</div></header>
<div class="wrap"><div class="article-cover reveal">{img(p['cover'], '', eager=True, width=2000)}</div>
<div class="article prose">{''.join(secs)}<div class="tags" style="margin-top:2.4em">{tags}</div></div></div>
</article>
<section class="section"><div class="wrap"><div class="section-head"><h2>Keep reading</h2></div>{post_rows(others)}</div></section>"""
    write(p["file"], layout(p["title"], p["summary"], body, "blog.html", p["cover"]))


def build_404() -> None:
    body = f"""<section class="wrap notfound">
  <span class="kicker" style="justify-content:center"><span class="dot"></span>Page not found</span>
  <h1>4<span class="serif">0</span>4</h1>
  <p class="lead" style="margin-inline:auto">Oops! We can't find that page. Why not head back home, or have a look at my work?</p>
  <div class="btns" style="justify-content:center"><a class="btn" href="./index.html">Back home</a><a class="btn btn--ghost" href="./work.html">See my work</a></div>
</section>"""
    write("404.html", layout("Page not found", "This page doesn't exist.", body))


def build_redirects() -> None:
    # Old URL with a space in it; keep it working.
    write("traffic monitoring.html", """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Traffic Monitoring</title><meta http-equiv="refresh" content="0; url=./traffic-monitoring.html">
<link rel="canonical" href="./traffic-monitoring.html"></head>
<body><a href="./traffic-monitoring.html">Traffic Monitoring case study</a></body></html>
""")


if __name__ == "__main__":
    print("Building site")
    build_index()
    build_work()
    build_about()
    for i, p in enumerate(PROJECTS):
        if p.get("slug"):
            build_project(i, p)
    build_blog()
    for p in POSTS:
        build_post(p)
    build_404()
    build_redirects()
    if MISSING:
        print("\nMissing files referenced by content:")
        for m in sorted(set(MISSING)):
            print("  ", m)
        raise SystemExit(1)
    print("Done.")
