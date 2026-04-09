from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import BlogPost
from .forms import BlogPostForm

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
    posts = BlogPost.objects.filter(status='Published')
    return render(request, 'blog_list.html', {'posts': posts})

def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, status='Published')
    
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
    Public facing view allowing any logged in user to submit a draft.
    """
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.status = 'Draft'
            post.save()
            messages.success(request, "Your article has been successfully submitted and is pending administrator approval!")
            return redirect('blog_list')
        else:
            print(form.errors) # For console debugging
            messages.error(request, "There was an error in your submission. Please check the fields below.")
    else:
        form = BlogPostForm()
        
    return render(request, 'blog_write.html', {'form': form})

@login_required
def admin_pending_blogs(request):
    """
    Dashboard view for admins and coordinators to see drafts.
    """
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        messages.error(request, "You do not have permission to access the approval queue.")
        return redirect('home')
        
    pending_posts = BlogPost.objects.filter(status='Draft').order_by('-created_at')
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
