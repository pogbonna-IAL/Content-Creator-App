/* eslint-disable */
/* 
 * Mock Service Worker - Empty stub to prevent 404 errors
 * This file is a placeholder. If you need MSW, install it:
 * npm install --save-dev msw
 * npx msw init public/
 */
// Empty service worker to prevent 404 errors
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', () => {
  self.clients.claim();
});

// No-op fetch handler
self.addEventListener('fetch', () => {
  // Do nothing - this is just a stub
});

