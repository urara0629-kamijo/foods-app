from django.db import models,transaction, IntegrityError
from django.utils.text import slugify
from datetime import datetime
from django.contrib.auth.models import User
import re
# Create your models here.

#食品モデル
class Food(models.Model):
    name = models.CharField('食品名', max_length=100)
    expiration_date = models.DateField('賞味期限')
    quantity = models.PositiveIntegerField('数量', default=1)
    jan_code = models.CharField('JANコード', max_length=13, blank=True, null=True)
    storage_location = models.CharField('収納場所', max_length=20)
    created_at = models.DateTimeField('登録日時', auto_now_add=True)
    maker = models.CharField('メーカー名', max_length=100, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='登録ユーザー')
    # ✅ Firestoreと照合するための一意なID
    doc_id = models.CharField('Firestore用ID', max_length=150, unique=True, editable=False)


def save(self, *args, **kwargs):
    if not self.doc_id:
        if isinstance(self.expiration_date, str):
            try:
                self.expiration_date = datetime.strptime(self.expiration_date, "%Y-%m-%d").date()
            except ValueError:
                self.expiration_date = datetime.today().date()

        if not self.expiration_date:
            self.expiration_date = datetime.today().date()

        safe_name = re.sub(r'[^\w\-]', '', self.name)[:50] or "unknown"
        base_id = f"{safe_name}_{self.expiration_date.strftime('%Y-%m-%d')}"
        suffix = 1

        while True:
            doc_id = f"{base_id}_{suffix}" if suffix > 1 else base_id
            self.doc_id = doc_id
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                break  # 成功したらループ終了
            except IntegrityError:
                suffix += 1  # doc_id を変更して再試行
    else:
        super().save(*args, **kwargs)



#消費食品モデル
class ConsumedFood(models.Model):
    food = models.ForeignKey('Food', on_delete=models.CASCADE, verbose_name='消費された食品')
    consumed_at = models.DateTimeField('消費日時', auto_now_add=True)
    quantity = models.PositiveIntegerField('消費量', default=1)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='ユーザー')

    def __str__(self):
        return f"{self.food.name} を {self.quantity}個 消費（{self.consumed_at.date()}）"

#通知モデル
class NotificationLog(models.Model):
    NOTIFICATION_TYPES = [
        ('expiry', '賞味期限通知'),
    ]

    food = models.ForeignKey('Food', on_delete=models.CASCADE, verbose_name='対象食品')
    message = models.TextField('通知メッセージ')
    notified_at = models.DateTimeField('通知日時', auto_now_add=True)
    type = models.CharField('通知種別', max_length=20, choices=NOTIFICATION_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='通知対象ユーザー')
    def __str__(self):
        return f"{self.food.name} に通知（{self.type}）"

#レシピモデル
class RecipeSuggestion(models.Model):
    title = models.CharField('レシピ名', max_length=200)
    ingredients = models.TextField('材料')
    url = models.URLField('レシピURL')
    suggested_for = models.ForeignKey('Food', on_delete=models.CASCADE, verbose_name='対象食品')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='ユーザー')
    suggested_at = models.DateTimeField('提案日時', auto_now_add=True)

    def __str__(self):
        return f"{self.title}（{self.suggested_for.name}向け）"

#JANコード読み取り、検索結果モデル
class RakutenProductCache(models.Model):
    jan_code = models.CharField('JANコード', max_length=13, unique=True)
    item_name = models.CharField('商品名', max_length=200)
    Company_name = models.CharField('メーカー名',max_length=40)
    item_price = models.PositiveIntegerField('価格',default=0)
    image_url = models.URLField('画像URL', blank=True, null=True)
    fetched_at = models.DateTimeField('取得日時', auto_now_add=True)

    def __str__(self):
        return f"{self.item_name}（JAN: {self.jan_code}）"
    
# ユーザープロフィールモデル（FCMトークン保存用）
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
