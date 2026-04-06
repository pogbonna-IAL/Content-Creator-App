# Brand source assets

Place your master PNGs here (then run `npm run import-brand` from `web-ui`):

| File | Purpose |
|------|---------|
| `logo-512.png` | Square logo (e.g. 512×512) — used for PWA icons, navbar `logo.png`, Apple touch icon |
| `favicon-64.png` | Favicon master (e.g. 64×64) — used for `favicon.ico` multi-size and `favicon.png` |

Regenerates files under `public/`: `icon-192.png`, `icon-512.png`, `apple-touch-icon.png`, `logo.png`, `favicon.png`, `favicon.ico`.
