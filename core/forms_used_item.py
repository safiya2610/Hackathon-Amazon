from django import forms

from .models import UsedItemListing


class UsedItemListingForm(forms.ModelForm):
    class Meta:
        model = UsedItemListing
        fields = ["condition", "price", "image", "video"]
        widgets = {
            "condition": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "video": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class SellerUsedItemListingForm(forms.ModelForm):
    class Meta:
        model = UsedItemListing
        fields = ["item", "condition", "price", "image", "video"]
        widgets = {
            "item": forms.Select(attrs={"class": "form-control"}),
            "condition": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "video": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Item
        self.fields['item'].queryset = Item.objects.filter(is_active=True)



