from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import NewsletterSubscriber


def _send_welcome_email(request, email):
    """Send a beautiful HTML welcome email to a new subscriber."""
    site_url = request.build_absolute_uri('/').rstrip('/')
    unsubscribe_url = request.build_absolute_uri(f'/newsletter/unsubscribe/{email}/')

    html_message = render_to_string('newsletter_welcome_email.html', {
        'site_url': site_url,
        'unsubscribe_url': unsubscribe_url,
    })
    plain_message = (
        "Welcome to the MedTour Newsletter!\n\n"
        "Thank you for subscribing. You'll receive updates about top hospitals, "
        "treatment guides, and freshly published articles.\n\n"
        f"Unsubscribe: {unsubscribe_url}"
    )

    msg = EmailMultiAlternatives(
        subject='Welcome to the MedTour Newsletter! 🎉',
        body=plain_message,
        from_email=settings.EMAIL_HOST_USER,
        to=[email],
    )
    msg.attach_alternative(html_message, "text/html")
    msg.send(fail_silently=True)


def send_new_article_notification(request, post):
    """
    Send a newsletter email to all active subscribers when a new article is published.
    Call this from blog views after approving/publishing a post.
    """
    active_subscribers = NewsletterSubscriber.objects.filter(is_active=True)
    if not active_subscribers.exists():
        return

    site_url = request.build_absolute_uri('/').rstrip('/')
    article_url = request.build_absolute_uri(post.get_absolute_url())

    for subscriber in active_subscribers:
        unsubscribe_url = request.build_absolute_uri(f'/newsletter/unsubscribe/{subscriber.email}/')

        html_message = render_to_string('newsletter_new_article_email.html', {
            'post': post,
            'site_url': site_url,
            'article_url': article_url,
            'unsubscribe_url': unsubscribe_url,
        })
        plain_message = (
            f"New article published on MedTour: {post.title}\n\n"
            f"{post.excerpt or ''}\n\n"
            f"Read it here: {article_url}\n\n"
            f"Unsubscribe: {unsubscribe_url}"
        )

        msg = EmailMultiAlternatives(
            subject=f"📰 New Article: {post.title}",
            body=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[subscriber.email],
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=True)


@require_POST
def subscribe(request):
    email = request.POST.get('email', '').strip().lower()

    if not email:
        return JsonResponse({'status': 'error', 'message': 'Please enter a valid email address.'}, status=400)

    if NewsletterSubscriber.objects.filter(email=email).exists():
        subscriber = NewsletterSubscriber.objects.get(email=email)
        if subscriber.is_active:
            return JsonResponse({'status': 'already', 'message': "You're already subscribed! We'll keep you updated."})
        else:
            subscriber.is_active = True
            subscriber.save()
            _send_welcome_email(request, email)
            return JsonResponse({'status': 'resubscribed', 'message': 'Welcome back! You have been re-subscribed.'})

    NewsletterSubscriber.objects.create(email=email)
    _send_welcome_email(request, email)

    return JsonResponse({'status': 'success', 'message': 'Thank you for subscribing! Check your inbox for a welcome email.'})


def unsubscribe(request, email):
    try:
        subscriber = NewsletterSubscriber.objects.get(email=email)
        subscriber.is_active = False
        subscriber.save()
        return render(request, 'newsletter_unsubscribe.html', {'email': email, 'success': True})
    except NewsletterSubscriber.DoesNotExist:
        return render(request, 'newsletter_unsubscribe.html', {'email': email, 'success': False})
