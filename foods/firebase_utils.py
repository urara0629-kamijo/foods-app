# firebase_utils.py
import firebase_admin
from firebase_admin import credentials

def initialize_firebase():
    if not firebase_admin._apps:
        cred_path = "my_django_project/firebase_config/serviceAccountKey.json"
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
