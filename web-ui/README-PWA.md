# PWA Setup Guide

This guide explains how to set up and use the Progressive Web App (PWA) features.

## Features

- ✅ Installable on mobile and desktop
- ✅ Offline fallback page
- ✅ Service worker for caching
- ✅ Mobile-optimized UX
- ✅ Auth and API routes excluded from caching

## Icon Generation

To generate PWA icons from the existing `icon.svg`:

### Option 1: Using the provided script

1. Install sharp (if not already installed):
   ```bash
   npm install --save-dev sharp
   ```

2. Run the icon generation script:
   ```bash
   node scripts/generate-icons.js
   ```

This will generate:
- `public/icon-192.png` (192x192)
- `public/icon-512.png` (512x512)

### Option 2: Manual generation

You can use any image editing tool or online converter to generate PNG icons from `public/icon.svg`:

- **icon-192.png**: 192x192 pixels
- **icon-512.png**: 512x512 pixels

## Testing PWA Features

### Development

PWA features are **disabled in development mode** by default. To test:

1. Build the production version:
   ```bash
   npm run build
   ```

2. Start the production server:
   ```bash
   npm start
   ```

3. Open Chrome DevTools → Application → Service Workers
4. Check "Offline" to test offline functionality

### Production

1. Deploy the application
2. Visit the site in a supported browser (Chrome, Edge, Safari, Firefox)
3. Look for the "Install" prompt or add to home screen option
4. Test offline functionality by disconnecting from the internet

## Mobile UX Improvements

The following mobile optimizations have been implemented:

- ✅ Responsive padding and spacing
- ✅ Touch-friendly button sizes (minimum 44px height)
- ✅ Improved text sizing for mobile screens
- ✅ Touch-optimized scrolling with `touch-pan-y`
- ✅ Better error message display on small screens
- ✅ Responsive grid layout (stacks on mobile)

## Cache Strategy

The service worker uses the following caching strategies:

- **API Routes**: NetworkOnly (never cached)
- **Auth Routes**: NetworkOnly (never cached)
- **Static Assets**: CacheFirst (cached for 30 days)
- **Pages**: NetworkFirst (cached for 24 hours with offline fallback)

## Offline Fallback

When offline, users will see the `/offline` page which:
- Shows a friendly offline message
- Lists what can be done offline
- Automatically redirects when connection is restored

## Troubleshooting

### Service Worker not updating

1. Clear browser cache and service workers
2. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
3. Unregister service worker in DevTools → Application → Service Workers

### Icons not showing

1. Ensure `icon-192.png` and `icon-512.png` exist in `public/`
2. Check `manifest.json` references the correct icon paths
3. Clear browser cache and reload

### PWA not installable

1. Ensure the site is served over HTTPS (required for PWA)
2. Check that `manifest.json` is accessible at `/manifest.json`
3. Verify service worker is registered (check DevTools → Application → Service Workers)

## Browser Support

- ✅ Chrome/Edge (Android, Desktop)
- ✅ Safari (iOS, macOS)
- ✅ Firefox (Desktop, Android)
- ⚠️ Some features may vary by browser

