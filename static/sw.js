const CACHE_NAME = 'smartheritage-v3';
const urlsToCache = [
    '/',
    '/static/manifest.json',
    '/static/img/icon-512.png',
    '/static/img/icon-192.png',
];

self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                return cache.addAll(urlsToCache);
            })
    );
    self.skipWaiting();
});

self.addEventListener('fetch', function(event) {
    var request = event.request;
    if (request.method !== 'GET') return;

    var isPage = request.mode === 'navigate';
    var isStatic = request.url.indexOf('/static/') !== -1;

    if (isPage) {
        event.respondWith(
            fetch(request)
                .then(function(networkResponse) {
                    var responseToCache = networkResponse.clone();
                    caches.open(CACHE_NAME).then(function(cache) {
                        cache.put(request, responseToCache);
                    });
                    return networkResponse;
                })
                .catch(function() {
                    return caches.match(request).then(function(cached) {
                        return cached || caches.match('/');
                    });
                })
        );
        return;
    }

    event.respondWith(
        caches.match(request)
            .then(function(response) {
                if (response) return response;
                return fetch(request).then(function(networkResponse) {
                    if (isStatic && networkResponse && networkResponse.status === 200) {
                        var responseToCache = networkResponse.clone();
                        caches.open(CACHE_NAME).then(function(cache) {
                            cache.put(request, responseToCache);
                        });
                    }
                    return networkResponse;
                });
            })
    );
});

self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('push', function(event) {
    var data = event.data ? event.data.json() : { title: 'SmartHeritage', body: 'Nueva notificacion' };
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/img/icon-192.png',
            badge: '/static/img/icon-192.png',
            vibrate: [200, 100, 200],
            data: { url: data.url || '/' }
        })
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});
