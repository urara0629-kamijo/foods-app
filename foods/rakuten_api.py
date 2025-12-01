# foods/rakuten_api.py
import requests
import json
import os
from django.conf import settings
import re

def clean_ingredient(name):
    # 先頭の記号（★☆●◎◇など）や空白を除去
    return re.sub(r'^[★☆●◎◇■□◆△▲▼▽※＊*・\s]+', '', name)

APP_ID = '1093784014530639652'  # 楽天アプリID

# 🔹 商品検索API（JANコードから商品情報を取得）
def fetch_rakuten_product(jan_code):
    url = 'https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706'
    params = {
        'format': 'json',
        'applicationId': APP_ID,
        'jan': jan_code
    }

    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()

        item = data['Items'][0]['Item'] if data.get('Items') and len(data['Items']) > 0 else {}
        return {
            'name': item.get('itemName', '不明な商品'),
            'jan_code': jan_code,
            'maker': item.get('shopName', '不明なメーカー'),
            'price': item.get('itemPrice', '価格不明')
        }

    except Exception as e:
        print(f"[楽天商品APIエラー] {e}")
        return {
            'name': '取得失敗',
            'jan_code': jan_code,
            'maker': '取得失敗',
            'price': '取得失敗'
        }
    
#カテゴリ名と食品名を照合
def find_matching_category_id(food_name, category_dict):
    for category_name in category_dict:
        if category_name in food_name:
            return category_dict[category_name]
    return None


# 🔹 レシピカテゴリランキングAPI（カテゴリIDからレシピ一覧を取得）
def fetch_recipe_ranking(category_id):
    # キャッシュパスを定義
    cache_dir = "foods/data/recipes_cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{category_id}.json")

    # キャッシュがあれば読み込む
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    # API呼び出し
    url = 'https://app.rakuten.co.jp/services/api/Recipe/CategoryRanking/20170426'
    params = {
        'format': 'json',
        'applicationId': APP_ID,
        'categoryId': category_id
    }

    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()

        recipes = []
        for i, r in enumerate(data.get("result", [])):
            recipes.append({
                "id": f"{category_id}-{i}",  # モーダル用ID
                "title": r.get("recipeTitle", "不明"),
                "url": r.get("recipeUrl", ""),
                "image": r.get("foodImageUrl", ""),
                "description": r.get("recipeDescription", ""),
                #材料の頭文字★とか●とかを取り除きたい
                "ingredients": [clean_ingredient(ing) for ing in r.get("recipeMaterial", [])],
                "time": r.get("cookingTime", "不明")
            })

        # キャッシュ保存
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)

        return recipes

    except Exception as e:
        print(f"[楽天レシピAPIエラー] {e}")
        return []

#食品名からレシピを取得する(直接使う用)
def fetch_recipes_by_food(food_name):
    # JSONから辞書を読み込む
    try:
        json_path = os.path.join(settings.BASE_DIR, 'foods', 'data', 'category_mapping.json')
        with open(json_path, encoding="utf-8") as f:
            category_dict = json.load(f)
    except Exception as e:
        print(f"[辞書読み込みエラー] {e}")
        return []

    # 食品名とカテゴリ名を照合
    category_id = find_matching_category_id(food_name, category_dict)
    if category_id:
        return fetch_recipe_ranking(category_id)
    else:
        print(f"[カテゴリ未発見] 食品名: {food_name} に対応するカテゴリIDが見つかりません。")
        return []
