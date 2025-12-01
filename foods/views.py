# Create your views here.
# foods/views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.text import slugify
from django.db import transaction, IntegrityError
from firebase_config.firebase_init import db
from firebase_admin import firestore,credentials,messaging,auth
from .firebase_utils import initialize_firebase
from foods.rakuten_api import fetch_rakuten_product,fetch_recipes_by_food
from foods.gemini_api import simplify_product_name, ask_gemini_for_category
from foods.utils import generate_doc_id
from django.contrib.auth.models import User
from .models import UserProfile
from .models import Food
from .forms import FoodForm
from datetime import date, timedelta, datetime

import json
import locale
import os
import firebase_admin

def messaging_view(request):
    return render(request,'foods/messaging.html')

# Firebaseトークン保存API
@csrf_exempt
def save_fcm_token(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        token = data.get('token')
        user_id = data.get('user_id')

        try:
            profile = UserProfile.objects.get(user_id=user_id)
            profile.fcm_token = token
            profile.save()
            return JsonResponse({'status': 'success'})
        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

# Firebase Cloud Messagingでプッシュ通知を送信する関数
def send_web_push(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
        webpush=messaging.WebpushConfig(
            headers={"TTL": "300"},
            notification={"icon": "/static/icon.png"}
        )
    )
    response = messaging.send(message)
    return response

# 賞味期限が近い食品の通知を送信する関数
def notify_expiring_items():
    today = datetime.today().date()
    threshold = today + timedelta(days=1)  # 明日が期限のものを通知

    items = Food.objects.filter(expiration_date=threshold)
    for item in items:
        user = item.user
        token = user.fcm_token  # ユーザーに紐づいたFCMトークン
        title = "消費期限が近づいています"
        body = f"{item.name} の期限は {item.expiration_date} です"
        send_web_push(token, title, body)

# ログインビュー
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "foods/login.html")

@csrf_exempt
def firebase_login(request):
    if request.method == "POST":
        data = json.loads(request.body)
        id_token = data.get("idToken")

        try:
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token["uid"]

            from django.contrib.auth.models import User
            user, created = User.objects.get_or_create(username=uid)

            from django.contrib.auth import login
            login(request, user)

            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

#初期登録
def signup_view(request):
    if request.method == "POST":
        # フォームからデータを取得してユーザー登録処理を行う
        pass
    return render(request, "foods/signup.html")

# 食品編集AJAX処理
@csrf_exempt
def food_edit_ajax(request, food_id):
    if request.method == 'POST':
        try:
            food = Food.objects.get(id=food_id)

            # Djangoモデルの更新
            food.name = request.POST.get('name', food.name)
            food.expiration_date = request.POST.get('expiration_date', food.expiration_date)
            food.quantity = request.POST.get('quantity', food.quantity)
            food.storage_location = request.POST.get('location', food.storage_location)
            food.maker = request.POST.get('maker', food.maker)
            food.price = request.POST.get('price', food.price)
            food.image_url = request.POST.get('image_url', food.image_url)

            food.save()  # Django DBに保存

            # Firestoreにも反映
            db.collection('foods').document(food.doc_id).update({
                "name": food.name,
                "expiration_date": food.expiration_date.strftime("%Y-%m-%d"),
                "quantity": food.quantity,
                "storage_location": food.storage_location,
                "maker": food.maker,
                "price": food.price,
                "image_url": food.image_url,
                "timestamp": firestore.SERVER_TIMESTAMP
            })

            return JsonResponse({'success': True})
        except Food.DoesNotExist:
            return JsonResponse({'success': False, 'error': '食品が見つかりません'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'})

def food_list(request):
    #一覧表示と検索
    query = request.GET.get('q')
    if query:
        foods = Food.objects.filter(name__icontains=query, quantity__gt=0)
    else:
        foods = Food.objects.filter(quantity__gt=0).order_by('expiration_date')

    food_list_json = json.dumps([
        {
            'id': f.id,
            'name': f.name,
            'jan_code': f.jan_code or '',
            'storage_location': f.storage_location,
            'expiration_date': f.expiration_date.strftime('%Y-%m-%d'),
            'quantity': f.quantity,
            'count':1
        }
        for f in foods
    ])

    return render(request, 'foods/list.html', {
        'foods': foods,
        'food_list_json': food_list_json
    })

# 一括削除処理
@csrf_exempt # 今回はテンプレート内にフォームがあり、CSRFトークンも含まれているため、このデコレータは必須ではないですが、残していても問題ありません。
def food_bulk_delete(request):
    if request.method == 'POST':
        # フロントエンドから送信されたIDのリストを取得
        selected_ids = request.POST.getlist('selected_foods')
        selected_ids = [int(id) for id in selected_ids if id.isdigit()]

        print("選択されたID:", selected_ids)

        # 1. Djangoデータベースから削除対象を取得
        foods_to_delete = Food.objects.filter(id__in=selected_ids)
        print("削除対象:", list(foods_to_delete.values_list('name', flat=True)))

        # 2. Firestoreから対応するドキュメントを削除
        for food in foods_to_delete:
            if food.doc_id:
                try:
                    # 'db'は適切に初期化されているものとします
                    db.collection("foods").document(food.doc_id).delete()
                    print(f"✅ Firestore削除: {food.doc_id}")
                except Exception as e:
                    # エラー発生時も処理を止めずにログを出力
                    print(f"⚠️ Firestore削除エラー: {food.doc_id} - {e}")
            else:
                print(f"⚠️ doc_idが空のためFirestore削除スキップ: {food.name}")

        # 3. Djangoデータベースから食品を一括削除
        foods_to_delete.delete()
        print(f"✅ Django側削除完了: {len(selected_ids)} 件")
        return redirect('food_list') # 処理後に一覧画面へリダイレクト

    return JsonResponse({'error': 'POSTメソッドのみ対応'}, status=400)

def home(request):#ホーム
    #ロケールを日本語に表示
    locale.setlocale(locale.LC_TIME,'ja_JP.UTF-8')
    today = date.today()
    weekday = today.strftime('%A')  # 英語表記 → 日本語化も可能
    #期限が近い食品を取得（例：3日以内）
    near_expiration = Food.objects.filter(expiration_date__lte=today + timedelta(days=3))
    #期限切れの食品を取得
    expired = Food.objects.filter(expiration_date__lt=today)
    return render(request, 'foods/home.html', {
        'today': today,
        'weekday': weekday,
        'near_expiration': near_expiration,#期限切れが近い食品リスト
        'expired_count': expired.count(), #期限切れの食品件数
        'count': near_expiration.count()  #期限切れが近い食品件数
    })

def home_stats_api(request):
    today = date.today()
    three_days_later = today + timedelta(days=3)

    # ✅ Firestore: 賞味期限が近い食品（今日〜3日後）
    near_expiry = 0
    expired = 0

    foods = db.collection("foods").stream()
    for doc in foods:
        data = doc.to_dict()
        expiry_str = data.get("expiration_date")
        if not expiry_str:
            continue

        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        if today <= expiry_date <= three_days_later:
            near_expiry += 1
        elif expiry_date < today:
            expired += 1

    # ✅ Firestore: 通知済み食品（重複なし）
    notified_docs = db.collection("notification_log").stream()
    notified_food_ids = set()
    for doc in notified_docs:
        data = doc.to_dict()
        food_id = data.get("food")
        if food_id:
            notified_food_ids.add(food_id)
    notified = len(notified_food_ids)
    return JsonResponse({
        "near_expiry": near_expiry,
        "notified": notified,
        "expired": expired
    })

# API：JANコードから商品情報を取得
@csrf_exempt
def fetch_product(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            jan_code = data.get('jan_code')

            if not jan_code:
                return JsonResponse({'error': 'JANコードが未指定です'}, status=400)
            #楽天検索APIで商品情報を取得
            product = fetch_rakuten_product(jan_code)
            #Gemini APIで商品名を簡潔化
            simplified_name = simplify_product_name(product['name'])

            return JsonResponse({
                'original_name': product['name'],
                'simplified_name': simplified_name,
                'jan_code': product['jan_code'],
                'maker': product['maker'],
                'price': product['price']
            })

        except Exception as e:
            return JsonResponse({'error': f'処理中にエラーが発生しました: {str(e)}'}, status=500)

    return JsonResponse({'error': 'POSTメソッドのみ対応'}, status=400)

# API：複数食品を一括登録
@csrf_exempt
def register_foods(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POSTメソッドのみ対応'}, status=400)

    foods_json = request.POST.get('foods_json')
    if not foods_json:
        return JsonResponse({'error': 'foods_jsonが空です'}, status=400)

    try:
        foods = json.loads(foods_json)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSONの解析に失敗しました'}, status=400)

    created = []
    for item in foods:
        expiration_str = item.get('expiration_date')
        try:
            expiration_date = datetime.strptime(expiration_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            print(f"⚠️ 日付変換エラー: {expiration_str}")
            expiration_date = datetime.today().date()

        name = item.get('name', '')
        doc_id = generate_doc_id(name, expiration_date)

        # Django側：既存のdoc_idがあれば更新、なければ新規
        food, _ = Food.objects.update_or_create(
                doc_id=doc_id,
                defaults={
                    'name': name,
                    'maker': item.get('maker', ''),
                    'jan_code': item.get('jan_code', ''),
                    'expiration_date': expiration_date,
                    'quantity': item.get('quantity', 1),
                    'storage_location': item.get('storage_location', '冷蔵庫'),
                    'user': request.user  # ← ここで紐づけ！
                }
            )
        created.append(food)

        # Firestore側：同じdoc_idに対してmerge保存（上書き or 新規どちらも対応）
        try:
            db.collection('foods').document(doc_id).set({
                "name": food.name,
                "expiration_date": food.expiration_date.strftime("%Y-%m-%d"),
                "quantity": food.quantity,
                "storage_location": food.storage_location,
                "jan_code": food.jan_code,
                "timestamp": firestore.SERVER_TIMESTAMP
            }, merge=True)
        except Exception as e:
            print(f"⚠️ Firestore保存エラー: {e}")

    return JsonResponse({'status': 'success', 'count': len(created)})


# 手動フォーム登録（Web画面から1件ずつ登録する場合）
def food_add(request):
    if request.method == 'POST':
        form = FoodForm(request.POST)
        if form.is_valid():
            food = form.save(commit=False)
            food.user = request.user
            food.save()
            if not food.doc_id:
                food.doc_id = generate_doc_id(food.name, food.expiration_date)

            # Django側：同じdoc_idがあれば上書き、なければ新規
            food, _ = Food.objects.update_or_create(
                doc_id=food.doc_id,
                defaults={
                    'name': food.name,
                    'maker': food.maker,
                    'jan_code': food.jan_code,
                    'expiration_date': food.expiration_date,
                    'quantity': food.quantity,
                    'storage_location': food.storage_location,
                }
            )

            # Firestore側：merge保存
            try:
                db.collection("foods").document(food.doc_id).set({
                    "name": food.name,
                    "expiration_date": food.expiration_date.strftime("%Y-%m-%d"),
                    "quantity": food.quantity,
                    "storage_location": food.storage_location,
                    "jan_code": food.jan_code,
                    "timestamp": firestore.SERVER_TIMESTAMP
                }, merge=True)
            except Exception as e:
                print(f"⚠️ Firestore保存エラー: {e}")

            return render(request, 'foods/add.html', {'success': True, 'count': 1})
    else:
        form = FoodForm()
    return render(request, 'foods/add.html', {'form': form})


# レシピ提案ビュー
def recipe_suggestion_view(request):
    today = date.today()
    three_days_later = today + timedelta(days=3)

    expiring_foods = Food.objects.filter(
        expiration_date__range=(today, three_days_later),
        quantity__gt=0
    ).order_by("expiration_date")

    return render(request, 'foods/recipe_suggestion.html', {
        'expiring_foods': expiring_foods
    })
# レシピ取得AJAX処理
@csrf_exempt
def fetch_recipes_ajax(request):
    if request.method == "POST":
        body = json.loads(request.body)
        selected_foods = body.get("foods", [])

        all_recipes = []
        for food in selected_foods:
            recipes = fetch_recipes_by_food(food)
            all_recipes.extend(recipes)

        # 最大6件に制限
        return JsonResponse({"recipes": all_recipes[:6]})


# JSON辞書でカテゴリIDを取得
def guess_category_id(ingredient_name):
    path = os.path.join(settings.BASE_DIR, 'foods', 'data', 'category_mapping.json')

    # 辞書を読み込む
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            mapping = json.load(f)
    else:
        mapping = {}

    # 辞書にあれば返す
    if ingredient_name in mapping:
        return mapping[ingredient_name]

    # 辞書になければ Gemini で推定
    category_id = ask_gemini_for_category(ingredient_name)

    # 辞書に追加して保存
    mapping[ingredient_name] = category_id
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    return category_id

# 消費記録の保存
@csrf_exempt
def record_consumption_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            consumed_items = data.get("consumed_items", [])
            used_at = data.get("used_at")
            recipe_info = data.get("recipe")

            # ✅ レシピ使用履歴をFirestoreに保存
            if recipe_info:
                db.collection("recipe_history").add({
                    "title": recipe_info.get("title"),
                    "url": recipe_info.get("url"),
                    "ingredients": recipe_info.get("ingredients"),
                    "used_at": used_at
                })

            for item in consumed_items:
                name = item["name"]
                expiry = item["expiry"]
                count = int(item.get("count", 0))
                doc_id = generate_doc_id(name, expiry)

                # 消費ログ保存
                db.collection("consumption_log").add({
                    "name": name,
                    "count": count,
                    "used_at": used_at
                })

                # Firestoreの数量更新
                doc = db.collection("foods").document(doc_id).get()
                if doc.exists:
                    current_qty = int(doc.to_dict().get("quantity", 0))
                    new_qty = max(current_qty - count, 0)
                    doc.reference.update({"quantity": new_qty})

                # Djangoの数量更新
                try:
                    food_obj = Food.objects.get(doc_id=doc_id)
                    food_obj.quantity = max(food_obj.quantity - count, 0)
                    food_obj.save()
                except Food.DoesNotExist:
                    print(f"Django側に食品が見つかりません: {doc_id}")
            return JsonResponse({"success": True})

        except Exception as e:
            print("Firestore保存エラー:", e)
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})




