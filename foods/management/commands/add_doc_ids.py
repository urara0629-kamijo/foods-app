from django.core.management.base import BaseCommand
from django.utils.text import slugify
from foods.models import Food
from datetime import datetime
from foods.utils import generate_doc_id  # ← views.pyから関数を共通化してimport

class Command(BaseCommand):
    help = '既存のFoodデータにユニークなdoc_idを付与する'

    def handle(self, *args, **kwargs):
        updated = 0
        existing_ids = set(Food.objects.exclude(doc_id__isnull=True).values_list('doc_id', flat=True))

        for food in Food.objects.filter(doc_id__isnull=True):
            attempt = 1
            while True:
                candidate_id = generate_doc_id(food.name, food.expiration_date, attempt)
                if candidate_id not in existing_ids:
                    break
                attempt += 1

            food.doc_id = candidate_id
            food.save()
            existing_ids.add(candidate_id)
            print(f"[doc_id付与] {food.name} → {food.doc_id}")
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'doc_idを付与した件数: {updated}'))

