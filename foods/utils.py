# foods/utils.py
import re
from datetime import datetime
from django.utils.text import slugify

def generate_doc_id(name, expiration_date, attempt=1, fallback='unknown', max_length=50):
    if isinstance(expiration_date, str):
        try:
            expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
        except ValueError:
            expiration_date = datetime.today().date()

    slug = slugify(name)
    if not slug:
        slug = re.sub(r'\W+', '_', name)[:max_length] or fallback

    base_id = f"{slug}_{expiration_date.strftime('%Y-%m-%d')}"
    return f"{base_id}_{attempt}" if attempt > 1 else base_id
