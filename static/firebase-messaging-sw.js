// Importa o script do Firebase
importScripts('/static/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging.js');

const firebaseConfig = {
    apiKey: "AIzaSyCx3huLfApzRJPETN8JwINUnVBoM1Krdvc",
    authDomain: "app-vaibes.firebaseapp.com",
    projectId: "app-vaibes",
    storageBucket: "app-vaibes.appspot.com",
    messagingSenderId: "842665045470",
    appId: "1:842665045470:web:edbe6c0cf3db4ac71c014f",
    measurementId: "G-3WTKSP88V9"
};

// Inicializa o Firebase
firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

// Manipula as mensagens recebidas em segundo plano
messaging.onBackgroundMessage((payload) => {
    console.log('Mensagem recebida em segundo plano:', payload);
    // Customize a notificação aqui
    self.registration.showNotification(payload.notification.title, {
        body: payload.notification.body,
        icon: payload.notification.icon
    });
});
