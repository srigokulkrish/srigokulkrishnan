# Site build

Every page is generated. Don't edit the `.html` files in the repo root by hand; the next build overwrites them.

```
python3 _build/build.py      # needs Python 3.9+, and Pillow for image sizes + WebP copies
```

- **Words:** `_build/content/site.json` (home, about, experience, testimonials, project list),
  `content/projects/<slug>.json` (case studies), `content/posts/<slug>.json` (writing).
- **Design system:** `assets/site/site.css` (tokens at the top, light and dark) and `assets/site/site.js`.
- **Images:** originals stay in `assets/img`. The build writes resized WebP copies to `assets/site/img`.
  The pages show those, and the lightbox opens the original.
- **Adding a project:** add an entry to `projects` in `site.json`, then a `content/projects/<slug>.json`.
- **Adding a post:** add `content/posts/<slug>.json`. It's published as `post-<slug>.html`.

Content blocks in a section's `body`: `p`, `sub`, `list`, `quote`, `img` (+`caption`), `video`,
`gallery`, `swatches`, `steps`, `pairs`.

The build stops with an error if any image or file it references is missing.
