// firebase-messaging-sw.js

importScripts('https://www.gstatic.com/firebasejs/10.5.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/10.5.0/firebase-messaging.js');

firebase.initializeApp({
  apiKey: "AIzaSyAoKK2n6PwmgTLxUfJQTSHxhZ8BwbqAXZI",
  authDomain: "foods-databases-f7d88.firebaseapp.com",
  projectId: "foods-databases-f7d88",
  storageBucket: "foods-databases-f7d88.firebasestorage.app",
  messagingSenderId: "825369391761",
  appId: "1:825369391761:web:3a8fcd6049579095eb0530"});

const messaging = firebase.messaging();

// バックグラウンド通知の受信処理
messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    // 任意のアイコン  icon: '/icon.png' 
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});
