# foods/urls.py
from django.urls import path
from . import views
from .views import save_fcm_token,messaging_view

urlpatterns = [
    path("", views.login_view, name="login"),  # ログインページ
    path("firebase-login/", views.firebase_login, name="firebase_login"),
    path("signup/", views.signup_view, name="signup"),# 初期登録ページ
    path('home/', views.home, name='home'),#ホーム
    path('list/', views.food_list,name='food_list'),#一覧
    path('food_bulk_delete/', views.food_bulk_delete, name='food_bulk_delete'),#一括削除
	path('<int:food_id>/edit-ajax/',views.food_edit_ajax, name='food_edit_ajax'),#�編集
    path('add/',views.food_add,name='food_add'),#追加
	path('fetch_product/',views.fetch_product,name='fetch_product'),# API商品情報取得
	path('register_foods/',views.register_foods,name='register_foods'),#食品登録
	path('recipe_suggestion/', views.recipe_suggestion_view, name='recipe_suggestion'),  # レシピ提案ペー
    path('fetch_recipes/', views.fetch_recipes_ajax, name='fetch_recipes_ajax'),  # レシピ取得AJAX
    path('record_consumption/', views.record_consumption_view, name='record_consumption'),  # 消費記録AJAX
    path("home_stats/", views.home_stats_api, name="home_stats_api"),
    path('api/save-token/',save_fcm_token),
    path('messaging/',messaging_view)
]
