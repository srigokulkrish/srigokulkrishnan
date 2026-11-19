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
NAV = [("Work", "work.html"), ("Services", "services.html"), ("About", "aboutme.html"), ("Writing", "blog.html")]
CONTACT = "./contact.html"
PAGES: list[str] = []  # every indexable page written, for sitemap.xml


def canonical(name: str) -> str:
    """Netlify serves /work for work.html, so the canonical URL drops the extension."""
    return f"{ORIGIN}/" if name == "index.html" else f"{ORIGIN}/{quote(name.removesuffix('.html'))}"


def person_ld() -> dict:
    return {
        "@type": "Person", "@id": f"{ORIGIN}/#person", "name": SITE["name"], "url": f"{ORIGIN}/",
        "jobTitle": SITE["role"], "email": f"mailto:{SITE['email']}",
        "image": f"{ORIGIN}/{url(SITE['about']['photo'].lstrip('./'))}",
        "address": {"@type": "PostalAddress", "addressCountry": "IN"},
        "worksFor": {"@type": "Organization", "name": "Cosmonus", "url": "https://www.cosmonus.com"},
        "knowsAbout": ["Product design", "UI/UX design", "Design systems", "Frontend development", "React", "Next.js", "Brand identity"],
        "sameAs": [u for _, u in SITE["social"]],
    }


def layout(title: str, description: str, body: str, current: str = "", image: str = "", whatsapp: bool = True,
           name: str = "", full_title: str = "", jsonld: list | None = None, index: bool = True) -> str:
    full = full_title or (title if title == SITE["name"] else f"{title} · {SITE['name']}")
    og_img = f'\n  <meta property="og:image" content="{ORIGIN}/{e(url(image.lstrip("./")))}">' if image else ""
    head_extra = ""
    if name:
        head_extra += f'\n  <link rel="canonical" href="{canonical(name)}">\n  <meta property="og:url" content="{canonical(name)}">'
        if index:
            PAGES.append(name)
    if not index:
        head_extra += '\n  <meta name="robots" content="noindex">'
    if jsonld:
        graph = json.dumps({"@context": "https://schema.org", "@graph": jsonld}, ensure_ascii=False).replace("</", "<\\/")
        head_extra += f'\n  <script type="application/ld+json">{graph}</script>'
    nav = "".join(
        f'<a href="./{href}"{" aria-current=\"page\"" if href == current else ""}>{label}</a>' for label, href in NAV
    ) + f'<a class="nav-cta" href="{CONTACT}"{" aria-current=\"page\"" if current == "contact.html" else ""}>Start a project</a>'
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
  <meta property="og:site_name" content="{e(SITE['name'])}">
  <meta name="twitter:card" content="summary_large_image">{head_extra}
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
      <nav class="nav" id="nav" aria-label="Main">{nav}</nav>
      <div class="header-actions">
        <a class="btn btn--sm header-cta" href="{CONTACT}">Start a project</a>
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
          <p class="footer-big">Have a product, website or idea you'd like help building?</p>
          <div class="btns"><a class="btn" href="{CONTACT}">Start a project {ARROW}</a><a class="btn btn--ghost" href="{wa_link()}" target="_blank" rel="noopener">WhatsApp me</a></div>
        </div>
        <div>
          <h3>Pages</h3>
          <ul><li><a href="./index.html">Home</a></li>{''.join(f'<li><a href="./{h}">{l}</a></li>' for l, h in NAV)}</ul>
        </div>
        <div>
          <h3>Elsewhere</h3>
          <ul>{socials}<li><a href="mailto:{email}">{e(email)}</a></li></ul>
        </div>
      </div>
      <div class="footer-base"><span>© <span data-year>{date.today().year}</span> {e(SITE['name'])}</span><span>Based in India · Working with clients worldwide</span></div>
    </div>
  </footer>
  <dialog class="lightbox" aria-label="Image preview">
    <button class="icon-btn" type="button" aria-label="Close">{ICON['close']}</button>
    <img src="" alt=""><p></p>
  </dialog>
  {wa_button() if whatsapp else ""}
  <script src="./assets/site/site.js" defer></script>
</body>
</html>
"""


WHATSAPP_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.61-.92-2.21-.24-.58-.49-.5-.67-.51l-.57-.01c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48 0 1.46 1.07 2.88 1.21 3.07.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.69.63.71.23 1.36.19 1.87.12.57-.09 1.76-.72 2.01-1.41.25-.69.25-1.29.17-1.41-.07-.12-.27-.2-.57-.35zM12.05 21.5h-.01a9.43 9.43 0 0 1-4.8-1.31l-.35-.2-3.57.93.95-3.48-.22-.36a9.4 9.4 0 0 1-1.45-5.02c0-5.2 4.24-9.43 9.45-9.43 2.52 0 4.89.98 6.67 2.77a9.37 9.37 0 0 1 2.76 6.67c0 5.2-4.24 9.43-9.43 9.43zm8.03-17.46A11.27 11.27 0 0 0 12.05.72C5.78.72.68 5.82.67 12.08c0 2 .52 3.96 1.52 5.68L.57 23.65l6.03-1.58a11.33 11.33 0 0 0 5.44 1.39h.01c6.26 0 11.36-5.1 11.37-11.36 0-3.04-1.18-5.89-3.33-8.04z"/></svg>'


def wa_link(text: str = "Hi Gokul, I'd like to talk about a project.") -> str:
    number = re.sub(r"\D", "", SITE["phone"])
    return f"https://wa.me/{number}?text={quote(text)}"


def wa_button() -> str:
    return (f'<a class="wa-fab" href="{e(wa_link())}" target="_blank" rel="noopener" '
            f'aria-label="Message me on WhatsApp">{WHATSAPP_SVG}<span>Message me</span></a>')


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
<figcaption>{img(a, n, width=120)}<div><strong>{e(n)}</strong><span>{e(r)}</span>{f'<span class="quote-project">{e(rest[0])}</span>' if rest and rest[0] else ''}</div></figcaption></figure>"""
        for q, n, r, a, *rest in SITE["testimonials"]
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


# ---------------------------------------------------------------- content blocks
def figure(src: str, caption: str = "", alt: str = "") -> str:
    cap = f"<figcaption>{e(caption)}</figcaption>" if caption else ""
    return f'<figure class="figure"><button class="frame" type="button" data-zoom="{e(url(thumb(src, 2400)))}" aria-label="Enlarge image">{img(src, alt or caption, width=1600)}</button>{cap}</figure>'


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


def cta(title: str = "Have a product, website or idea you'd like help building?") -> str:
    return f"""<section class="section"><div class="wrap"><div class="cta reveal">
  <span class="kicker" style="color:inherit;opacity:.7"><span class="dot"></span>Let's work together</span>
  <h2>{e(title)}</h2>
  <p class="cta-lead">Tell me what you're building. I'll come back with questions, a plan and a clear next step.</p>
  <div class="btns"><a class="btn" href="{CONTACT}">Start a project {ARROW}</a><a class="btn btn--ghost" href="{e(wa_link())}" target="_blank" rel="noopener">Message me on WhatsApp</a></div>
</div></div></section>"""


def head(kicker: str, title: str, hid: str, link: str = "") -> str:
    return (f'<div class="section-head reveal"><div><span class="kicker"><span class="dot"></span>{e(kicker)}</span>'
            f'<h2 id="{hid}" style="margin-top:14px">{title}</h2></div>{link}</div>')


def process_tiles() -> str:
    return '<ol class="tiles tiles--steps">' + "".join(
        f'<li class="tile reveal"><span class="num">0{i}</span><h3>{e(n)}</h3><p>{e(d)}</p></li>'
        for i, (n, d) in enumerate(SITE["process"], 1)) + "</ol>"


def service_summaries() -> str:
    return '<div class="tiles">' + "".join(
        f'<a class="tile tile--link reveal" href="./services.html#{s["slug"]}"><span class="num">0{i}</span><h3>{e(s["name"])}</h3>'
        f'<p>{e(s["for"])}</p><span class="tile-more">What\'s included {ARROW}</span></a>'
        for i, s in enumerate(SITE["services"], 1)) + "</div>"


def stack_rows() -> str:
    return '<div class="rows">' + "".join(
        f'<div class="row reveal"><span class="row-name">{e(n)}</span><p class="row-text">{e(d)}</p><span></span></div>'
        for n, d in SITE["stack"]) + "</div>"


# ---------------------------------------------------------------- pages
def build_index() -> None:
    h = SITE["hero"]
    selected = [p for p in PROJECTS if p.get("slug") in ("stayonmap", "happenous", "fluidwork", "cosmonus")]
    title = e(h["title"]).replace(e(h["serif"]), f'<span class="serif">{e(h["serif"])}</span>')
    logos = "".join(img(src, name) for name, src in SITE["clients"])
    a = SITE["about"]
    body = f"""<section class="hero"><div class="wrap hero-grid">
  <div>
    <span class="kicker reveal"><span class="dot"></span>{e(h['kicker'])}</span>
    <h1 class="reveal">{title}</h1>
    <p class="lead reveal">{e(h['lead'])}</p>
    <div class="btns reveal"><a class="btn" href="./work.html">Explore my work {ARROW}</a><a class="btn btn--ghost" href="{CONTACT}">Start a project</a></div>
    <p class="availability reveal"><span class="pulse" aria-hidden="true"></span>{e(h['availability'])}</p>
  </div>
  {img(a['photo'], SITE['name'], 'hero-photo reveal', eager=True, width=600)}
</div></section>
<section class="logos" aria-label="Companies I've worked with"><div class="wrap"><span>Companies I've worked with</span>{logos}</div></section>

<section class="section" id="work" aria-labelledby="selected-work">
  <div class="wrap">
    {head("Selected work", "Products I've shipped and brands I've built", "selected-work", f'<a class="btn btn--ghost" href="./work.html">All projects {ARROW}</a>')}
    <p class="lead section-lead reveal">{e(h['proof'])}</p>
    <div class="grid grid--2">{''.join(card(p, feature=True) for p in selected)}</div>
  </div>
</section>

<section class="section" aria-labelledby="what-i-do">
  <div class="wrap">
    {head("Services", "How I can help", "what-i-do", f'<a class="btn btn--ghost" href="./services.html">All services {ARROW}</a>')}
    {service_summaries()}
  </div>
</section>

<section class="section" aria-labelledby="how-i-work">
  <div class="wrap">
    {head("How I work", "Simple, direct and transparent", "how-i-work")}
    {process_tiles()}
  </div>
</section>

<section class="section" aria-labelledby="experience">
  <div class="wrap">
    {head("Experience", "Where I've been building", "experience")}
    {experience_rows()}
  </div>
</section>

{quotes_block()}

<section class="section" aria-labelledby="about-me">
  <div class="wrap about-teaser">
    <div class="about-teaser-photo reveal">{img(a['photo'], SITE['name'], width=600)}</div>
    <div class="reveal">
      <span class="kicker"><span class="dot"></span>About</span>
      <h2 id="about-me" style="margin:14px 0 20px">Designer and builder, working with you directly.</h2>
      <div class="prose"><p>{e(a['intro'][0])}</p><p>{e(a['intro'][1])}</p></div>
      <div class="btns" style="margin-top:28px"><a class="btn btn--ghost" href="./aboutme.html">More about me {ARROW}</a></div>
    </div>
  </div>
</section>
{cta()}"""
    desc = (f"{SITE['name']} is a product designer and frontend developer helping startups and businesses worldwide "
            "design and build web apps, websites, MVPs and brands.")
    write("index.html", layout(SITE["name"], desc, body, "", "./assets/img/stayonmap/card-map.jpg", name="index.html",
                               full_title=f"{SITE['name']} · Product Designer & Frontend Developer",
                               jsonld=[person_ld(), {"@type": "WebSite", "@id": f"{ORIGIN}/#website", "url": f"{ORIGIN}/", "name": SITE["name"], "publisher": {"@id": f"{ORIGIN}/#person"}},
                                       {"@type": "ProfessionalService", "@id": f"{ORIGIN}/#service", "name": f"{SITE['name']}: product design and development",
                                        "url": f"{ORIGIN}/", "founder": {"@id": f"{ORIGIN}/#person"}, "areaServed": "Worldwide", "email": SITE["email"],
                                        "image": f"{ORIGIN}/assets/img/stayonmap/card-map.jpg",
                                        "makesOffer": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["name"], "description": s["for"]}} for s in SITE["services"]]}]))


GROUPS = [
    ("products", "My products", "Designed and built end to end, and live today."),
    ("client", "Client work", "Brand, web and product work for companies and founders."),
    ("exercise", "Case studies & design exercises", "Timed design sprints and self-initiated case studies that show how I think."),
]


def build_work() -> None:
    sections = []
    for key, label, lead in GROUPS:
        items = [p for p in PROJECTS if p.get("group") == key]
        sections.append(f"""<section class="section work-group" aria-labelledby="g-{key}"><div class="wrap">
  <div class="section-head reveal"><div><h2 id="g-{key}">{e(label)}</h2><p class="muted" style="margin:12px 0 0">{e(lead)}</p></div></div>
  <div class="grid grid--2">{''.join(card(p, feature=key != 'exercise') for p in items)}</div>
</div></section>""")
    body = f"""<section class="hero"><div class="wrap">
  <span class="kicker reveal"><span class="dot"></span>Work</span>
  <h1 class="reveal">Products, brands and <span class="serif">websites</span>.</h1>
  <p class="lead reveal">Two products I designed and built myself, brand and web work for clients, and design exercises that show how I approach a problem.</p>
</div></section>
{''.join(sections)}
{cta()}"""
    write("work.html", layout("Work", "Selected work by Sri Gokul Krishnan: the StayOnMap and Happenous products, brand and web work for clients like Fluid.Work, and UX case studies.", body, "work.html", "./assets/img/stayonmap/card-map.jpg", name="work.html"))


def build_services() -> None:
    blocks_ = []
    for i, s in enumerate(SITE["services"], 1):
        inc = "".join(f"<li>{e(x)}</li>" for x in s["includes"])
        blocks_.append(f"""<article class="service reveal" id="{s['slug']}" aria-labelledby="s-{s['slug']}">
  <div class="service-head"><span class="num">0{i}</span><h2 id="s-{s['slug']}">{e(s['name'])}</h2></div>
  <dl class="service-body">
    <div><dt>Who it's for</dt><dd>{e(s['for'])}</dd></div>
    <div><dt>The problem it solves</dt><dd>{e(s['problem'])}</dd></div>
    <div><dt>What's included</dt><dd><ul>{inc}</ul></dd></div>
    <div><dt>What you receive</dt><dd>{e(s['receive'])}</dd></div>
    <div><dt>See it in</dt><dd>{e(s['proof'])}</dd></div>
  </dl>
  <a class="btn btn--ghost" href="{CONTACT}?type={quote(s['name'])}">Start a project like this {ARROW}</a>
</article>""")
    body = f"""<section class="hero"><div class="wrap">
  <span class="kicker reveal"><span class="dot"></span>Services</span>
  <h1 class="reveal">From idea to <span class="serif">shipped</span> product.</h1>
  <p class="lead reveal">Four ways I work with founders and businesses. Each one can stand alone, and they work best together: the same person designs it and builds it, so nothing gets lost in a handover.</p>
  <div class="btns reveal"><a class="btn" href="{CONTACT}">Start a project {ARROW}</a></div>
</div></section>
<section class="section" style="padding-top:0"><div class="wrap services">{''.join(blocks_)}</div></section>
<section class="section" aria-labelledby="how-i-work"><div class="wrap">
  {head("How I work", "Simple, direct and transparent", "how-i-work")}
  {process_tiles()}
</div></section>
<section class="section" aria-labelledby="stack"><div class="wrap">
  {head("Tools", "What I design and build with", "stack")}
  {stack_rows()}
</div></section>
{cta()}"""
    write("services.html", layout("Services", "Product design and UI/UX, website design and development, MVP design and development, and branding, by Sri Gokul Krishnan for startups and businesses worldwide.", body, "services.html", "./assets/img/happenous/card-activities.jpg", name="services.html",
                                  jsonld=[person_ld()] + [{"@type": "Service", "name": s["name"], "description": f"{s['for']} {s['receive']}", "provider": {"@id": f"{ORIGIN}/#person"}, "areaServed": "Worldwide"} for s in SITE["services"]]))


PROJECT_TYPES = [s["name"] for s in SITE["services"]] + ["Not sure yet"]
TIMELINES = ["As soon as possible", "Within a month", "In 1–3 months", "Just exploring"]


def build_contact() -> None:
    types = "".join(f'<option value="{e(t)}">{e(t)}</option>' for t in PROJECT_TYPES)
    times = "".join(f'<option value="{e(t)}">{e(t)}</option>' for t in TIMELINES)
    body = f"""<section class="hero"><div class="wrap">
  <span class="kicker reveal"><span class="dot"></span>Start a project</span>
  <h1 class="reveal">Let's talk about <span class="serif">your project</span>.</h1>
  <p class="lead reveal">Tell me what you're building. The quickest way to reach me is WhatsApp. If you'd rather write it out, use the form and I'll reply by email.</p>
</div></section>
<section class="section" style="padding-top:0"><div class="wrap contact-grid">
  <form class="form reveal" name="project" method="POST" action="/thanks" data-netlify="true" netlify-honeypot="company-website">
    <input type="hidden" name="form-name" value="project">
    <p class="hp"><label>Leave this empty <input name="company-website" tabindex="-1" autocomplete="off"></label></p>
    <div class="field-row">
      <label class="field"><span>Name <em>*</em></span><input name="name" autocomplete="name" required></label>
      <label class="field"><span>Email <em>*</em></span><input type="email" name="email" autocomplete="email" required></label>
    </div>
    <label class="field"><span>Company <small>optional</small></span><input name="company" autocomplete="organization"></label>
    <div class="field-row">
      <label class="field"><span>Project type</span><select name="project-type" id="project-type">{types}</select></label>
      <label class="field"><span>Timeline</span><select name="timeline">{times}</select></label>
    </div>
    <label class="field"><span>About the project <em>*</em></span><textarea name="description" rows="6" required placeholder="What are you building, who is it for, and what would a great result look like?"></textarea></label>
    <button class="btn" type="submit">Send project details {ARROW}</button>
    <p class="form-note">Fields marked * are required. Your details are only used to reply to you.</p>
  </form>
  <aside class="contact-side reveal" aria-label="Other ways to reach me">
    <a class="wa-card" href="{e(wa_link())}" target="_blank" rel="noopener">{WHATSAPP_SVG}<span><strong>Message me on WhatsApp</strong><small>The fastest way to start a conversation</small></span></a>
    <p class="muted" style="margin:20px 0 4px">Or email</p>
    <p><a href="mailto:{SITE['email']}">{e(SITE['email'])}</a></p>
    <h2 class="side-title">What happens next</h2>
    <ol class="next-steps">
      <li><strong>I read your message</strong><span>and reply personally, with any questions I have.</span></li>
      <li><strong>We talk it through</strong><span>on a call or in messages, whichever suits you.</span></li>
      <li><strong>You get a plan</strong><span>with scope, timeline and price, before any work starts.</span></li>
    </ol>
  </aside>
</div></section>
<script>
  (function () {{
    var t = new URLSearchParams(location.search).get('type'), s = document.getElementById('project-type');
    if (t && s) for (var i = 0; i < s.options.length; i++) if (s.options[i].value === t) s.selectedIndex = i;
  }})();
</script>"""
    write("contact.html", layout("Start a project", "Start a project with Sri Gokul Krishnan: product design, websites, MVPs and branding. Send the project form or message on WhatsApp.", body, "contact.html", name="contact.html", whatsapp=False))


def build_thanks() -> None:
    body = f"""<section class="wrap notfound">
  <span class="kicker" style="justify-content:center"><span class="dot"></span>Message sent</span>
  <h1 style="font-size:clamp(48px,8vw,96px)">Thank <span class="serif">you</span>.</h1>
  <p class="lead" style="margin-inline:auto">Your project details have reached me. I'll read them and reply by email with any questions and the next step. If it's urgent, message me on WhatsApp.</p>
  <div class="btns" style="justify-content:center"><a class="btn" href="{e(wa_link())}" target="_blank" rel="noopener">WhatsApp me</a><a class="btn btn--ghost" href="./work.html">Look at more work</a></div>
</section>"""
    write("thanks.html", layout("Thank you", "Your project details were sent.", body, name="thanks.html", index=False, whatsapp=False))


def build_about() -> None:
    a = SITE["about"]
    socials = "".join(f'<li><a href="{u}" rel="me noopener" target="_blank">{n}</a></li>' for n, u in SITE["social"])
    body = f"""<section class="hero"><div class="wrap">
  <span class="kicker reveal"><span class="dot"></span>About</span>
  <h1 class="reveal">Designer, developer and <span class="serif">founder</span>.</h1>
</div></section>
<section class="section" style="padding-top:0"><div class="wrap about-grid">
  <div class="prose reveal">{''.join(f'<p>{e(p)}</p>' for p in a['intro'])}
    <h3>Work with me</h3>
    <p>I work directly with founders and businesses worldwide. <a href="{CONTACT}">Tell me about your project</a>, or message me on <a href="{e(wa_link())}" target="_blank" rel="noopener">WhatsApp</a>.</p>
    <ul class="contact-list"><li><a href="mailto:{SITE['email']}">{e(SITE['email'])}</a></li>{socials}</ul>
  </div>
  <div class="about-photo reveal">{img(a['photo'], SITE['name'], eager=True, width=900)}</div>
</div></section>

<section class="section" aria-labelledby="how-i-work">
  <div class="wrap">
    {head("How I work", "Simple, direct and transparent", "how-i-work")}
    {process_tiles()}
  </div>
</section>

<section class="section" aria-labelledby="stack">
  <div class="wrap">
    {head("Tools", "What I design and build with", "stack", f'<a class="btn btn--ghost" href="./services.html">Services {ARROW}</a>')}
    {stack_rows()}
  </div>
</section>

<section class="section" aria-labelledby="experience">
  <div class="wrap">
    {head("Experience", "Where I've been building", "experience")}
    {experience_rows()}
  </div>
</section>
{quotes_block()}
{cta()}"""
    write("aboutme.html", layout("About", f"About {SITE['name']}: product designer and frontend developer, founder of Cosmonus (StayOnMap, Happenous) and previously the AstusX design studio.", body, "aboutme.html", a["photo"], name="aboutme.html",
                                 jsonld=[person_ld(), {"@type": "ProfilePage", "url": canonical("aboutme.html"), "mainEntity": {"@id": f"{ORIGIN}/#person"}}]))


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
<div class="wrap"><a class="next-project reveal" href="./{nxt['slug']}.html"><span class="kicker"><span class="dot"></span>Next project</span><span class="big">{e(nxt['title'])} →</span></a></div>
{cta("Want something like this for your company?")}"""
    ld = {"@type": "CreativeWork", "name": d["title"], "headline": d.get("tagline") or p["summary"], "description": p["summary"],
          "url": canonical(f"{p['slug']}.html"), "image": f"{ORIGIN}/{url(p['card'].lstrip('./'))}", "creator": {"@id": f"{ORIGIN}/#person"}}
    write(f"{p['slug']}.html", layout(p["title"], f"{p['title']}: {p['summary']}", body, "work.html", p["card"],
                                      name=f"{p['slug']}.html", jsonld=[person_ld(), ld]))


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
    write("blog.html", layout("Writing", f"Writing by {SITE['name']} on product design, design systems and building StayOnMap and Happenous.", body, "blog.html", POSTS[0]["cover"], name="blog.html"))


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
    ld = {"@type": "BlogPosting", "headline": p["title"], "description": p["summary"], "datePublished": p["date"],
          "url": canonical(p["file"]), "image": f"{ORIGIN}/{url(p['cover'].lstrip('./'))}", "author": {"@id": f"{ORIGIN}/#person"}}
    write(p["file"], layout(p["title"], p["summary"], body, "blog.html", p["cover"], name=p["file"], jsonld=[person_ld(), ld]))


def build_404() -> None:
    body = f"""<section class="wrap notfound">
  <span class="kicker" style="justify-content:center"><span class="dot"></span>Page not found</span>
  <h1>4<span class="serif">0</span>4</h1>
  <p class="lead" style="margin-inline:auto">Oops! We can't find that page. Why not head back home, or have a look at my work?</p>
  <div class="btns" style="justify-content:center"><a class="btn" href="./index.html">Back home</a><a class="btn btn--ghost" href="./work.html">See my work</a></div>
</section>"""
    write("404.html", layout("Page not found", "This page doesn't exist.", body, index=False))


def build_redirects() -> None:
    # Old URL with a space in it; keep it working.
    write("traffic monitoring.html", """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Traffic Monitoring</title><meta http-equiv="refresh" content="0; url=./traffic-monitoring.html">
<meta name="robots" content="noindex"><link rel="canonical" href="https://www.srigokulkrishnan.com/traffic-monitoring"></head>
<body><a href="./traffic-monitoring.html">Traffic Monitoring case study</a></body></html>
""")


def build_seo_files() -> None:
    today = date.today().isoformat()
    urls = "".join(f"  <url><loc>{canonical(n)}</loc><lastmod>{today}</lastmod></url>\n" for n in PAGES)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n")


if __name__ == "__main__":
    print("Building site")
    build_index()
    build_work()
    build_services()
    build_contact()
    build_thanks()
    build_about()
    for i, p in enumerate(PROJECTS):
        if p.get("slug"):
            build_project(i, p)
    build_blog()
    for p in POSTS:
        build_post(p)
    build_404()
    build_redirects()
    build_seo_files()
    if MISSING:
        print("\nMissing files referenced by content:")
        for m in sorted(set(MISSING)):
            print("  ", m)
        raise SystemExit(1)
    print("Done.")
