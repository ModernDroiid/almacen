// ============================================================
// SERVICE WORKER — MÍNIMO, A PROPÓSITO
//
// Su único trabajo es cumplir el requisito técnico que pide
// Chrome/Brave/Edge para que la app se pueda "Instalar" como si
// fuera una app de escritorio (icono propio, ventana sin barra
// de direcciones).
//
// NO cachea nada. Esta app vive de datos en vivo contra la API
// (productos, stock, notificaciones...), así que cachear el HTML
// o el JS agresivamente podría dejar a alguien usando una versión
// vieja de la app sin que se dé cuenta — mucho más riesgoso que
// el pequeño beneficio de velocidad que daría el caché.
// ============================================================

self.addEventListener('install', (event) => {
    // Activa esta versión del service worker de inmediato, sin
    // esperar a que se cierren las pestañas/ventanas abiertas.
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
    // Deja pasar toda petición directo a la red, sin tocar caché.
    event.respondWith(fetch(event.request));
});
