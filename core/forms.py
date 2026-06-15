from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

from .forms_used_item import UsedItemListingForm

PAYMENT_CHOICES = (
    ('S', 'Stripe'),
    ('P', 'PayPal'),
    ('C', 'Cash on Delivery (COD)')
)


class CheckoutForm(forms.Form):
    phone_number = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Phone Number',
        'class': 'form-control'
    }))
    location = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Delivery Location',
        'class': 'form-control'
    }))
    street_address = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': '1234 Main St',
        'class': 'form-control'
    }))
    apartment_address = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Apartment or suite',
        'class': 'form-control'
    }))
    country = CountryField(blank_label='(select country)').formfield(widget=CountrySelectWidget(attrs={
        'class': 'custom-select d-block w-100'

    }))

    zip = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control'
    }))
    same_shipping_address = forms.BooleanField(required=False)
    save_info = forms.BooleanField(required=False)
    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES)


class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Promo code'
    }))


class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4
    }))
    email = forms.EmailField()

from .models import LocalResellItem

class LocalResellItemForm(forms.ModelForm):
    class Meta:
        model = LocalResellItem
        fields = ['title', 'price', 'image', 'location', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item Name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price (e.g. 50.00)'}),
            'image': forms.FileInput(attrs={'class': 'form-control-file'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Location (e.g. New York, Zip 10001)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your item...'}),
        }

