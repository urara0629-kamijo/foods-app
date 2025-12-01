from django import forms
from .models import Food

class FoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = ['name', 'expiration_date', 'quantity', 'storage_location', 'jan_code']

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        super().__init__(*args, **kwargs)
        for key, value in initial.items():
            if key in self.fields:
                self.fields[key].initial = value
