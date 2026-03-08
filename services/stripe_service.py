import stripe

from config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(
    job_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    customer_email=None,
):
    """Create a Stripe Checkout session. Returns (session_id, session_url)."""
    kwargs = dict(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"job_id": job_id},
    )
    if customer_email:
        kwargs["customer_email"] = customer_email
    session = stripe.checkout.Session.create(**kwargs)
    return session.id, session.url


def construct_webhook_event(payload: bytes, sig_header: str):
    """Validate and parse a Stripe webhook event."""
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
