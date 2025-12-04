import firebase_admin
import os, json
from firebase_admin import credentials, firestore, messaging

firebase_key_json = os.getenv("FIREBASE_KEY_JSON")
if not firebase_key_json:
    raise Exception("FIREBASE_KEY_JSON is not set")

try:
    cred_dict = json.loads(firebase_key_json)
    cred = credentials.Certificate(cred_dict)

    # すでに初期化済みか確認してから initialize_app を呼ぶ
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    db = firestore.client()

except Exception as e:
    raise Exception(f"Firebase init failed: {e}")

