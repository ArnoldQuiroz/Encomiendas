// 📱 Service Worker — Sistema de Encomiendas PWA
const CACHE_NAME = 'encomiendas-v1';
const STATIC_ASSETS = [
    '/static/css/styles.css',
    '/static/js/main.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
];

// Install: precache de assets estáticos
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activate: borra caches viejos
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((names) =>
            Promise.all(names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n)))
        )
    );
    self.clients.claim();
});

// Fetch: network-first para HTML/API, cache-first para estáticos
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // No cachear POST ni admin
    if (event.request.method !== 'GET') return;
    if (url.pathname.startsWith('/admin/') || url.pathname.startsWith('/api/v1/')) return;

    // Estáticos: cache-first
    if (url.pathname.startsWith('/static/') ||
        url.hostname.includes('jsdelivr') ||
        url.hostname.includes('cdnjs') ||
        url.hostname.includes('unpkg')) {
        event.respondWith(
            caches.match(event.request).then((cached) =>
                cached || fetch(event.request).then((response) => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    }
                    return response;
                })
            )
        );
        return;
    }

    // HTML/Páginas: network-first con fallback a cache
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                }
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});
