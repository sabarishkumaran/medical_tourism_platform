from django.contrib import admin
from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'content', 'author__username', 'author__first_name')
    prepopulated_fields = {'slug': ('title',)}
    
    # Organize fields in the add/edit form
    fieldsets = (
        ('Article Context', {
            'fields': ('title', 'slug', 'author', 'status')
        }),
        ('Media & Summary', {
            'fields': ('image', 'excerpt')
        }),
        ('Content', {
            'fields': ('content',)
        }),
    )
