from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import date, timedelta
from foods.models import Food, NotificationLog
from firebase_admin import messaging
from foods.firebase_utils import initialize_firebase

class Command(BaseCommand):
    help = '賞味期限が近い食品に通知を送信します'

    def handle(self, *args, **kwargs):
        initialize_firebase()

        today = date.today()
        threshold = today + timedelta(days=1)  # 明日が期限の食品を対象

        # すでに通知済みの doc_id を取得（重複防止）
        notified_doc_ids = NotificationLog.objects.filter(
            type='expiry',
            notified_at__date=today
        ).values_list('food__doc_id', flat=True)

        # 通知対象の食品を抽出
        foods_to_notify = Food.objects.filter(
            expiration_date=threshold
        ).exclude(doc_id__in=notified_doc_ids)

        for food in foods_to_notify:
            user = User.objects.get(id=food.user_id)  # user_id が保存されている前提
            token = getattr(user, 'fcm_token', None)  # ユーザーにFCMトークンがある前提

            if not token:
                self.stdout.write(self.style.WARNING(f"{user.username} にFCMトークンが未登録"))
                continue

            title = "消費期限が近づいています"
            body = f"{food.name} の期限は {food.expiration_date} です"

            try:
                message = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    token=token,
                    webpush=messaging.WebpushConfig(
                        headers={"TTL": "300"},
                        notification={"icon": "/static/icon.png"}
                    )
                )
                messaging.send(message)

                # 通知ログを保存
                NotificationLog.objects.create(
                    food=food,
                    message=body,
                    type='expiry',
                    user=user
                )

                self.stdout.write(self.style.SUCCESS(f"通知送信: {food.name} → {user.username}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"通知失敗: {food.name} → {user.username} | {e}"))
