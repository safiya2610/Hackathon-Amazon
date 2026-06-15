from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, RefundForm
from .forms_used_item import UsedItemListingForm, SellerUsedItemListingForm
from .models import (
    Item,
    OrderItem,
    Order,
    BillingAddress,
    Payment,
    Coupon,
    Refund,
    Category,
    UserPoints,
    UsedItemListing,
    UsedItemPurchase,
    UsedItemCartItem,
    ProductReview,
)



import random
import string
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False
            }
            return render(self.request, "payment.html", context)

        messages.warning(self.request, "u have not added a billing address")
        return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100)

        try:
            charge = stripe.Charge.create(
                amount=amount,  # cents
                currency="usd",
                source=token
            )

            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            order.ordered = True
            order.payment = payment
            order.ref_code = create_ref_code()
            order.save()

            # Process any used item listings in the order
            for order_item in order.items.all():
                if order_item.used_item_listing:
                    listing = order_item.used_item_listing
                    listing.is_active = False
                    listing.save()

                    # Award green points to the buyer: 10 green points per $1 sold price
                    buyer_points, _ = UserPoints.objects.get_or_create(user=self.request.user)
                    points_awarded = int(listing.price * 10)
                    buyer_points.points += points_awarded
                    buyer_points.save()

                    # Create a UsedItemPurchase record
                    UsedItemPurchase.objects.create(
                        buyer=self.request.user,
                        listing=listing,
                        sold_price=listing.price,
                        points_awarded=points_awarded,
                    )

            messages.success(self.request, "Order was successful")
            return redirect("/")

        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.error(self.request, f"{err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError:
            messages.error(self.request, "RateLimitError")
            return redirect("/")

        except stripe.error.InvalidRequestError:
            messages.error(self.request, "Invalid parameters")
            return redirect("/")

        except stripe.error.AuthenticationError:
            messages.error(self.request, "Not Authentication")
            return redirect("/")

        except stripe.error.APIConnectionError:
            messages.error(self.request, "Network Error")
            return redirect("/")

        except stripe.error.StripeError:
            messages.error(self.request, "Something went wrong")
            return redirect("/")

        except Exception:
            messages.error(self.request, "Serious Error occured")
            return redirect("/")


class HomeView(ListView):
    template_name = "index.html"
    queryset = Item.objects.filter(is_active=True)
    context_object_name = 'items'


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            return render(self.request, 'order_summary.html', {'object': order})
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("/")


class ShopView(ListView):
    model = Item
    paginate_by = 6
    template_name = "shop.html"


class ItemDetailView(DetailView):
    model = Item
    template_name = "product-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.object

        context["used_listings"] = item.used_listings.filter(is_active=True, is_donation=False).order_by("-created_at")
        context["reviews"] = item.reviews.all().order_by("-created_at")

        if self.request.user.is_authenticated:
            points_obj, _ = UserPoints.objects.get_or_create(user=self.request.user)
            context["user_points"] = points_obj.points
        else:
            context["user_points"] = 0
        context["sell_form"] = None

        return context
    def post(self, request, *args, **kwargs):
        item = self.get_object()
        action = request.POST.get("action")

        if action == "add_to_cart":
            if not request.user.is_authenticated:
                return redirect("core:product", slug=item.slug)

            listing_id = request.POST.get("listing_id")
            listing = get_object_or_404(
                UsedItemListing,
                id=listing_id,
                item=item,
                is_active=True,
            )

            # Don't let the seller add their own listing
            if listing.seller == request.user:
                messages.warning(request, "You cannot add your own listing to cart.")
                return redirect("core:product", slug=item.slug)

            # Get or create the active order for the user
            order_qs = Order.objects.filter(user=request.user, ordered=False)
            if order_qs.exists():
                order = order_qs[0]
            else:
                order = Order.objects.create(user=request.user, ordered_date=timezone.now())

            # Check if this used listing is already in the order
            if order.items.filter(used_item_listing=listing).exists():
                messages.info(request, "This used item is already in your cart.")
            else:
                # Create OrderItem with used_item_listing
                order_item = OrderItem.objects.create(
                    user=request.user,
                    item=item,
                    used_item_listing=listing,
                    quantity=1,
                    ordered=False
                )
                order.items.add(order_item)
                messages.success(request, "Used item was added to your cart.")

            return redirect("core:order-summary")

        elif action == "add_review":
            if not request.user.is_authenticated:
                return redirect("core:product", slug=item.slug)
            
            content = request.POST.get("content")
            if content:
                ProductReview.objects.create(
                    item=item,
                    user=request.user,
                    content=content
                )
                messages.success(request, "Review submitted successfully.")

                # Trigger Gemini API to analyze all reviews and create a size recommendation
                reviews = item.reviews.all()
                if reviews.count() > 0:
                    try:
                        import requests
                        from django.conf import settings
                        API_KEY = settings.GEMINI_API_KEY
                        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
                        
                        reviews_text = "\n".join([f"- {r.content}" for r in reviews])
                        prompt = f"""
                        Analyze the following customer reviews for the product '{item.title}'.
                        Determine if there are any sizing fit issues or order fulfillment issues mentioned.
                        If customers say it's small, recommend sizing up. If large, recommend sizing down.
                        If customers mention receiving the wrong size or wrong item, warn the buyer about potential fulfillment inaccuracies.
                        Keep it to 1 concise, helpful sentence. If there are no clear issues or recommendations, return 'No sizing recommendation available.'
                        
                        Reviews:
                        {reviews_text}
                        """
                        headers = {'Content-Type': 'application/json'}
                        payload = {"contents": [{"parts": [{"text": prompt}]}]}
                        
                        response = requests.post(gemini_url, headers=headers, json=payload, timeout=10)
                        if response.status_code == 200:
                            raw_text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                            item.size_recommendation = raw_text
                            item.save()
                    except Exception as e:
                        print("Gemini sizing analysis error:", e)

            return redirect("core:product", slug=item.slug)

        messages.error(request, "Invalid action")
        return redirect("core:product", slug=item.slug)
class CategoryView(View):
    def get(self, *args, **kwargs):
        category = Category.objects.get(slug=self.kwargs['slug'])
        items = Item.objects.filter(category=category, is_active=True)
        context = {
            'object_list': items,
            'category_title': category,
            'category_description': category.description,
            'category_image': category.image
        }
        return render(self.request, "category.html", context)


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }
            return render(self.request, "checkout.html", context)

        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address')
                country = form.cleaned_data.get('country')
                zip = form.cleaned_data.get('zip')
                payment_option = form.cleaned_data.get('payment_option')

                billing_address = BillingAddress(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip,
                    address_type='B'
                )
                billing_address.save()
                order.billing_address = billing_address
                order.save()

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                if payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')

                messages.warning(self.request, "Invalid payment option select")
                return redirect('core:checkout')

        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("core:order-summary")


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "Item qty was updated.")
            return redirect("core:order-summary")

        order.items.add(order_item)
        messages.info(request, "Item was added to your cart.")
        return redirect("core:order-summary")

    ordered_date = timezone.now()
    order = Order.objects.create(user=request.user, ordered_date=ordered_date)
    order.items.add(order_item)
    messages.info(request, "Item was added to your cart.")
    return redirect("core:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False,
            )[0]
            order.items.remove(order_item)
            messages.info(request, "Item was removed from your cart.")
            return redirect("core:order-summary")

        messages.info(request, "Item was not in your cart.")
        return redirect("core:product", slug=slug)

    messages.info(request, "u don't have an active order.")
    return redirect("core:product", slug=slug)


@login_required
def remove_used_from_cart(request, pk):
    order_item = get_object_or_404(OrderItem, pk=pk, user=request.user, ordered=False)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(id=order_item.id).exists():
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "Used item was removed from your cart.")
    return redirect("core:order-summary")


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False,
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item qty was updated.")
            return redirect("core:order-summary")

        messages.info(request, "Item was not in your cart.")
        return redirect("core:product", slug=slug)

    messages.info(request, "u don't have an active order.")
    return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        return Coupon.objects.get(code=code)
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")

            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        return render(self.request, "request_refund.html", {'form': form})

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')

            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist")
                return redirect("core:request-refund")

        return redirect("core:request-refund")


class BuyerDashboardView(LoginRequiredMixin, View):
    template_name = "buyer.html"

    def get(self, *args, **kwargs):
        buyer_points_obj, _ = UserPoints.objects.get_or_create(user=self.request.user)
        purchases = (
            UsedItemPurchase.objects.filter(buyer=self.request.user)
            .select_related("listing", "listing__item")
            .order_by("-purchased_at")
        )
        recent_purchases = purchases[:6]

        context = {
            "user_points": buyer_points_obj.points,
            "purchases_count": purchases.count(),
            "recent_purchases": recent_purchases,
            "purchases": purchases,
        }
        return render(self.request, self.template_name, context)


class SellerDashboardView(LoginRequiredMixin, View):
    template_name = "seller.html"

    def get(self, *args, **kwargs):
        listings = (
            UsedItemListing.objects.filter(seller=self.request.user)
            .select_related("item")
            .order_by("-created_at")
        )
        active_listings = listings.filter(is_active=True)
        sold_listings = listings.filter(is_active=False)
        recent_sold_listings = sold_listings[:6]

        context = {
            "listings": listings,
            "active_listings_count": active_listings.count(),
            "sold_listings_count": sold_listings.count(),
            "total_listings_count": listings.count(),
            "recent_sold_listings": recent_sold_listings,
            "sell_form": SellerUsedItemListingForm(),
        }
        return render(self.request, self.template_name, context)

    def post(self, *args, **kwargs):
        form = SellerUsedItemListingForm(self.request.POST or None, self.request.FILES or None)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = self.request.user
            listing.is_active = True

            if listing.price is None or listing.price <= 0:
                messages.error(self.request, "Price must be greater than 0")
                return redirect("core:seller-dashboard")

            if listing.price >= listing.item.price:
                messages.error(
                    self.request,
                    f"Used price must be less than the new item price (${listing.item.price})"
                )
                return redirect("core:seller-dashboard")

            # Check if there is an uploaded image to analyze using Gemini
            if listing.image:
                import base64
                import json
                import requests

                def detect_donation_suggestion(image_file):
                    from django.conf import settings
                    api_key = settings.GEMINI_API_KEY
                    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
                    
                    try:
                        image_file.seek(0)
                        image_data = image_file.read()
                        image_file.seek(0)  # Reset for saving
                        
                        image_base64 = base64.b64encode(image_data).decode('utf-8')
                        mime_type = getattr(image_file, 'content_type', 'image/jpeg')
                    except Exception as e:
                        print("Error reading uploaded image for Gemini API:", e)
                        return False, None

                    headers = {
                        "Content-Type": "application/json"
                    }

                    payload = {
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": (
                                            "You are an AI classifier for a green/eco-friendly marketplace. "
                                            "Analyze the uploaded image. Check if the product in the image is a book, "
                                            "OR if it is very old, torn, or worn-out clothing. "
                                            "You must respond ONLY with a valid JSON object of the format: "
                                            '{"is_book_or_old_cloth": true/false, "reason": "book" or "very old cloth" or "other description"}'
                                        )
                                    },
                                    {
                                        "inlineData": {
                                            "mimeType": mime_type,
                                            "data": image_base64
                                        }
                                    }
                                ]
                            }
                        ],
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }

                    for model in models:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                        try:
                            response = requests.post(url, headers=headers, json=payload, timeout=12)
                            if response.status_code == 200:
                                result = response.json()
                                text_response = result['candidates'][0]['content']['parts'][0]['text']
                                data = json.loads(text_response.strip())
                                is_suggest = data.get("is_book_or_old_cloth", False)
                                reason = data.get("reason", "")
                                return is_suggest, reason
                            else:
                                print(f"Gemini API returned status code {response.status_code} for model {model}: {response.text}")
                        except Exception as e:
                            print(f"Error calling Gemini API with model {model}:", e)
                            
                    return False, None

                suggest, reason = detect_donation_suggestion(listing.image)
                if suggest:
                    listing.suggest_donation = True
                    listing.donation_reason = reason
                    messages.info(
                        self.request,
                        f"🌱 Your listing was added! Note: Gemini detected this item as a '{reason}'. "
                        "Would you consider donating it to support sustainability? Your selling option remains active."
                    )
                else:
                    messages.success(self.request, "Your used listing has been successfully added!")
            else:
                messages.success(self.request, "Your used listing has been successfully added!")

            listing.save()
        else:
            messages.error(self.request, "Invalid listing details. Please try again.")

        return redirect("core:seller-dashboard")


class UsedCartView(LoginRequiredMixin, View):
    template_name = "used_cart.html"

    def get(self, request, *args, **kwargs):
        cart_items = (
            UsedItemCartItem.objects.filter(user=request.user, listing__is_active=True)
            .select_related("listing", "listing__item", "listing__seller")
            .order_by("-added_at")
        )

        # Remove cart items whose listings are no longer active
        UsedItemCartItem.objects.filter(user=request.user, listing__is_active=False).delete()

        total_price = sum(ci.listing.price for ci in cart_items)
        total_points = sum(int(ci.listing.price * 10) for ci in cart_items)

        buyer_points_obj, _ = UserPoints.objects.get_or_create(user=request.user)

        context = {
            "cart_items": cart_items,
            "total_price": total_price,
            "total_points": total_points,
            "user_points": buyer_points_obj.points,
        }
        return render(request, self.template_name, context)


@login_required
def remove_used_cart_item(request, item_id):
    cart_item = get_object_or_404(UsedItemCartItem, id=item_id, user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from your used-item cart.")
    return redirect("core:used-cart")


@login_required
def buy_used_cart(request):
    if request.method != "POST":
        return redirect("core:used-cart")

    cart_items = (
        UsedItemCartItem.objects.filter(user=request.user, listing__is_active=True)
        .select_related("listing")
    )

    if not cart_items.exists():
        messages.warning(request, "Your used-item cart is empty.")
        return redirect("core:used-cart")

    buyer_points, _ = UserPoints.objects.get_or_create(user=request.user)
    total_points_awarded = 0

    for ci in cart_items:
        listing = ci.listing
        points_awarded = int(listing.price * 10)
        total_points_awarded += points_awarded

        UsedItemPurchase.objects.create(
            buyer=request.user,
            listing=listing,
            sold_price=listing.price,
            points_awarded=points_awarded,
        )

        listing.is_active = False
        listing.save()

    buyer_points.points += total_points_awarded
    buyer_points.save()

    # Clear the cart
    UsedItemCartItem.objects.filter(user=request.user).delete()

    messages.success(
        request,
        f"Purchase successful! You earned {total_points_awarded} green points.",
    )
    return redirect("core:used-cart")


@login_required
def mark_as_donation(request, pk):
    listing = get_object_or_404(UsedItemListing, pk=pk, seller=request.user)
    listing.is_donation = True
    listing.price = 0.0
    listing.save()
    messages.success(request, f"🌱 '{listing.item.title}' has been successfully marked as a donation item and is listed for free!")
    return redirect("core:seller-dashboard")


class DonationsView(ListView):
    template_name = "donations.html"
    context_object_name = "donation_listings"

    def get_queryset(self):
        return UsedItemListing.objects.filter(is_donation=True, is_active=True).select_related('item', 'seller').order_by("-created_at")


@login_required
def claim_donation(request, pk):
    listing = get_object_or_404(UsedItemListing, pk=pk, is_donation=True, is_active=True)
    if listing.seller == request.user:
        messages.error(request, "You cannot claim your own donated item.")
        return redirect("core:donations")

    # Claim the donation
    listing.is_active = False
    listing.save()

    # Create UsedItemPurchase record with $0 price
    UsedItemPurchase.objects.create(
        buyer=request.user,
        listing=listing,
        sold_price=0.0,
        points_awarded=0
    )

    messages.success(request, f"🎉 You have successfully claimed '{listing.item.title}' for free! It is now ordered for you.")
    return redirect("core:buyer-dashboard")


from .models import LocalResellItem, LocalResellOrder
from .forms import LocalResellItemForm

class NearbyProductsView(ListView):
    template_name = "nearby_products.html"
    context_object_name = "products"

    def get_queryset(self):
        qs = LocalResellItem.objects.filter(is_sold=False).order_by("-created_at")
        location_query = self.request.GET.get('location')
        if location_query:
            qs = qs.filter(location__icontains=location_query)
        return qs

class UploadNearbyProductView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        form = LocalResellItemForm()
        return render(self.request, "upload_nearby.html", {'form': form})
        
    def post(self, *args, **kwargs):
        form = LocalResellItemForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.seller = self.request.user
            item.save()
            messages.success(self.request, "Your local item was successfully listed!")
            return redirect('core:nearby-products')
        messages.error(self.request, "Error listing your item. Check the form.")
        return render(self.request, "upload_nearby.html", {'form': form})

@login_required
def buy_local_item(request, pk):
    item = get_object_or_404(LocalResellItem, pk=pk, is_sold=False)
    if item.seller == request.user:
        messages.warning(request, "You cannot buy your own item.")
        return redirect("core:nearby-products")
        
    item.is_sold = True
    item.save()
    
    LocalResellOrder.objects.create(
        buyer=request.user,
        item=item
    )
    
    messages.success(request, f"You successfully claimed {item.title}! Arrange a local meetup with the seller to pay ${item.price} and collect your item (0 Delivery Charge).")
    return redirect("core:nearby-products")
