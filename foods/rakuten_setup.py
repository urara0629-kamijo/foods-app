# foods/rakuten_api.py
import requests
import pandas as pd
import json
import os

APP_ID = '1093784014530639652'  # 楽天アプリID
    
#楽天レシピカテゴリ一覧API
def fetch_rakuten_recipe_categories():
    
    url = 'https://app.rakuten.co.jp/services/api/Recipe/CategoryList/20170426'
    params = {
        'format': 'json',
        'applicationId': APP_ID,
    }

    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        json_data = res.json()

        rows = []
        parent_dict = {}

        # DataFrame初期化
        df = pd.DataFrame(columns=['category1', 'category2', 'category3', 'categoryId', 'categoryName'])

        # 大カテゴリ
        for cat in json_data['result']['large']:
            rows.append({
                'category1': cat['categoryId'],
                'category2': "",
                'category3': "",
                'categoryId': cat['categoryId'],
                'categoryName': cat['categoryName']
            })

        # 中カテゴリ
        for cat in json_data['result']['medium']:
            full_id = f"{cat['parentCategoryId']}-{cat['categoryId']}"
            rows.append({
                'category1': cat['parentCategoryId'],
                'category2': cat['categoryId'],
                'category3': "",
                'categoryId': full_id,
                'categoryName': cat['categoryName']
            })
            parent_dict[str(cat['categoryId'])] = str(cat['parentCategoryId'])

            # 小カテゴリ
        category_dict = {}
        for cat in json_data['result']['small']:
            medium_id = str(cat['parentCategoryId'])
            large_id = parent_dict.get(medium_id)
            if large_id:
                full_id = f"{large_id}-{medium_id}-{cat['categoryId']}"
                rows.append({
                    'category1': large_id,
                    'category2': medium_id,
                    'category3': cat['categoryId'],
                    'categoryId': full_id,
                    'categoryName': cat['categoryName']
                })
                category_dict[cat['categoryName']] = full_id

        # DataFrameに変換
        df = pd.DataFrame(rows)

        # 保存先フォルダを作成
        os.makedirs("data", exist_ok=True)

        # DataFrameをCSV保存（開発用）
        df.to_csv("data/rakuten_category_full.csv", index=False, encoding="utf-8-sig")

        # 辞書をJSON保存（アプリ用）
        with open("data/category_mapping.json", "w", encoding="utf-8") as f:
            json.dump(category_dict, f, ensure_ascii=False, indent=2)

        print("カテゴリ一覧と辞書を保存しました！")

    except Exception as e:
        print(f"[楽天カテゴリ取得エラー] {e}")
    
if __name__ == "__main__":
    fetch_rakuten_recipe_categories()