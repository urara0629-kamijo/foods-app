# firebase_config/firebase_init.py
import firebase_admin
from firebase_admin import credentials, firestore,messaging

# firebaseサービスアカウントキーのパス()
cred = credentials.Certificate('firebase_config/serviceAccountKey.json')

# Firebase初期化（すでに初期化済みか確認）
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Firestoreクライアントを取得
db = firestore.client()
