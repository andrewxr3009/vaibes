importScripts("https://js.pusher.com/beams/service-worker.js");

// service-worker.js
self.addEventListener('push', function(event) {
    const data = event.data.json();
    
    const options = {
        body: data.body,
        icon: '/staticivaive-icon.png',
        badge: '/staticivaive-icon.png'
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});
