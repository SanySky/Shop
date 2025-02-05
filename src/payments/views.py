from decimal import Decimal

import stripe
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View
from accounts.models import User
from shop.models import Cart, CartItem

from orders.models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


@method_decorator(decorator=never_cache, name="get")
class PaymentProcess(View):
    @csrf_exempt
    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=self.request.user.pk)
        cart = Cart.objects.get(user=user)
        cart_items = CartItem.objects.filter(cart=cart)

        session_data = {
            "mode": "payment",
            "success_url": request.build_absolute_uri(reverse('shop:index')),
            "cancel_url": request.build_absolute_uri(reverse('payment:canceled')),
            "line_items": []
        }

        for item in cart_items:
            session_data["line_items"].append(
                {
                    "price_data": {
                        "unit_amount": int(item.price * Decimal("100")),
                        "currency": "usd",
                        "product_data": {
                            "name": item.product.product.name
                        },
                    },
                    "quantity": item.quantity
                }
            )
            cart.delete_product(item)

        order = Order.objects.get(pk=kwargs["id"])
        order.order_status = "Paid"
        order.save()

        session = stripe.checkout.Session.create(**session_data)
        return redirect(session.url, code=303)


class PaymentCanceled(TemplateView):
    template_name = "payments/canceled.html"
