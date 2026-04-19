from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import BlogPost
from .forms import BlogPostForm
from django.db.models import Q
from newsletter.views import send_new_article_notification

def send_blog_approval_email(request, post):
    """
    Helper to send a styled HTML email when a blog post is published.
    """
    author = post.author
    if not author.email:
        return
        
    subject = 'Your MedTour Article has been Published!'
    absolute_url = request.build_absolute_uri(post.get_absolute_url())
    
    html_message = render_to_string('blog_approval_email.html', {
        'author': author,
        'post': post,
        'absolute_url': absolute_url,
    })
    
    # Plain text fallback
    plain_message = f"Hello {author.first_name if author.first_name else author.username},\n\nGreat news! Your article '{post.title}' has just been approved and published.\n\nView it here: {absolute_url}"
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@medtour.com',
            [author.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        print(f"Failed to send blog approval email: {e}")

def blog_list(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    
    posts = BlogPost.objects.filter(status='Published')
    
    if query:
        posts = posts.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) |
            Q(excerpt__icontains=query)
        )
        
    if category:
        posts = posts.filter(category=category)
        
    trending_posts = BlogPost.objects.filter(status='Published').order_by('-views_count')[:5]
        
    return render(request, 'blog_list.html', {
        'posts': posts,
        'trending_posts': trending_posts,
        'current_category': category,
        'search_query': query
    })

from django.db.models import Q, F

# ... (rest of imports)

def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, status='Published')
    
    # Increment view count safely
    BlogPost.objects.filter(pk=post.pk).update(views_count=F('views_count') + 1)
    post.refresh_from_db()
    
    # Get previous and next posts for navigation
    # Fetching them from the same 'Published' query
    previous_post = BlogPost.objects.filter(status='Published', created_at__lt=post.created_at).first()
    next_post = BlogPost.objects.filter(status='Published', created_at__gt=post.created_at).order_by('created_at').first()
    
    return render(request, 'blog_detail.html', {
        'post': post,
        'previous_post': previous_post,
        'next_post': next_post
    })

@login_required
def blog_write(request):
    """
    Public facing view allowing any logged in user to save a draft or submit for review.
    """
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            if 'submit' in request.POST:
                post.status = 'Draft'
                post.submitted_for_review = True
                post.save()
                messages.success(request, "Your article has been submitted for administrator review!")
            else:  # save_draft
                post.status = 'Draft'
                post.submitted_for_review = False
                post.save()
                messages.success(request, "Article saved as draft. You can continue editing it from My Articles.")
            return redirect('my_articles')
        else:
            messages.error(request, "There was an error in your submission. Please check the fields below.")
    else:
        form = BlogPostForm()

    return render(request, 'blog_write.html', {'form': form})


@login_required
def my_articles(request):
    """
    Author dashboard: shows all posts written by the logged-in user.
    """
    posts = BlogPost.objects.filter(author=request.user).order_by('-created_at')
    draft_count = posts.filter(status='Draft').count()
    published_count = posts.filter(status='Published').count()
    return render(request, 'my_articles.html', {
        'posts': posts,
        'draft_count': draft_count,
        'published_count': published_count,
    })


@login_required
def author_blog_edit(request, pk):
    """
    Allows authors to edit their own posts.
    - Drafts can be re-saved or submitted for review.
    - Published posts are reverted to Draft (pending review) on save.
    """
    post = get_object_or_404(BlogPost, pk=pk, author=request.user)

    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated = form.save(commit=False)
            was_published = post.status == 'Published'
            if 'submit' in request.POST or was_published:
                updated.status = 'Draft'
                updated.submitted_for_review = True  # Goes into admin review queue
                updated.save()
                if was_published:
                    messages.success(request, "Your edits have been saved and sent back for admin review before republishing.")
                else:
                    messages.success(request, "Article submitted for review!")
            else:
                updated.status = 'Draft'
                updated.submitted_for_review = False  # Personal draft — hidden from admin
                updated.save()
                messages.success(request, "Draft saved successfully.")
            return redirect('my_articles')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = BlogPostForm(instance=post)

    return render(request, 'author_blog_edit.html', {'form': form, 'post': post})

@login_required
def admin_pending_blogs(request):
    """
    Dashboard view for admins and coordinators to see drafts.
    """
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        messages.error(request, "You do not have permission to access the approval queue.")
        return redirect('home')
        
    pending_posts = BlogPost.objects.filter(status='Draft', submitted_for_review=True).order_by('-created_at')
    return render(request, 'admin_pending_blogs.html', {'pending_posts': pending_posts})

@login_required
def approve_blog(request, pk):
    """
    Fast action to mark a blog post as published and notify the author.
    """
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        return redirect('home')
        
    post = get_object_or_404(BlogPost, pk=pk)
    
    if request.method == "POST":
        post.status = 'Published'
        post.save()
        send_blog_approval_email(request, post)
        send_new_article_notification(request, post)
        messages.success(request, f"Article '{post.title}' successfully published!")
        return redirect('admin_pending_blogs')
        
    return redirect('admin_pending_blogs')

@login_required
def admin_blog_edit(request, pk):
    """
    Administrative view to edit any blog post before approval/publishing.
    """
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('home')
        
    post = get_object_or_404(BlogPost, pk=pk)
    
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            
            # Check if admin wants to publish immediately
            if 'publish' in request.POST:
                post.status = 'Published'
                post.save()
                send_blog_approval_email(request, post)
                send_new_article_notification(request, post)
                messages.success(request, "Article updated and published successfully!")
            else:
                post.save()
                messages.success(request, "Article draft updated successfully.")
                
            return redirect('admin_pending_blogs')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = BlogPostForm(instance=post)
        
    return render(request, 'admin_blog_edit.html', {
        'form': form,
        'post': post
    })
