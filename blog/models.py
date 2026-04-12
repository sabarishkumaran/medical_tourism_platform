from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from accounts.models import User

STATUS_CHOICES = (
    ('Draft', 'Draft'),
    ('Published', 'Published'),
)

CATEGORY_CHOICES = (
    ('Treatments', 'Treatments'),
    ('Country Guides', 'Country Guides'),
    ('Health Tips', 'Health Tips'),
    ('Patient Stories', 'Patient Stories'),
)

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Treatments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    excerpt = models.TextField(blank=True, help_text="A short summary of the article")
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Draft')
    views_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Handle slug collision
            original_slug = self.slug
            count = 1
            while BlogPost.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)
        
    def get_absolute_url(self):
        return reverse('blog_detail', kwargs={'slug': self.slug})