# foods/gemini_api.py
import google.generativeai as genai
import requests

# 🔹 Gemini APIを直接呼び出す関数
def call_gemini_api(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    api_key = "AIzaSyCC-aRrM9Z8VevcADhxDDzMgrQydi2FIu0"  # ← うららさんのAPIキーをここに

    headers = {
        "Content-Type": "application/json"
    }

    body = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    res = requests.post(f"{url}?key={api_key}", headers=headers, json=body)
    res.raise_for_status()
    data = res.json()

    # 最初の候補のテキストを返す
    return data["candidates"][0]["content"]["parts"][0]["text"]

# 🔹 Geminiで商品名を簡潔化
def simplify_product_name(product_name):
    prompt = f"次の商品名を短く簡潔にしてください：『{product_name}』"
    return call_gemini_api(prompt)

# GeminiでカテゴリIDを推定（例）
def ask_gemini_for_category(name):
    prompt = f"楽天レシピAPIのカテゴリIDで、食材「{name}」に最も近いものは？ID形式で答えてください。"
    return call_gemini_api(prompt)