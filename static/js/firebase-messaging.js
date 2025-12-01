// Firebase SDKの初期化
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  projectId: "YOUR_PROJECT_ID",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

// Service Worker の登録
navigator.serviceWorker.register('/firebase-messaging-sw.js')
  .then(registration => {
    messaging.useServiceWorker(registration);
    console.log("Service Worker registered:", registration);
  });
