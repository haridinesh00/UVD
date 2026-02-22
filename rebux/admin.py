from django.contrib import admin
from django.utils.html import format_html
from .models import PuzzleLevel

@admin.register(PuzzleLevel)
class PuzzleLevelAdmin(admin.ModelAdmin):
    # These are the columns that will show up in the main admin table
    list_display = ('level_number', 'correct_answer', 'image_1_preview', 'image_2_preview')
    
    # Adds a search bar so you can quickly find a specific puzzle by its answer
    search_fields = ('correct_answer',)
    
    # Keeps everything neatly sorted by level number
    ordering = ('level_number',)

    # 🪄 The Magic: Render the Unsplash URLs as actual images in the dashboard
    def image_1_preview(self, obj):
        if obj.image_1_url:
            return format_html('<img src="{}" style="height: 60px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />', obj.image_1_url)
        return "No Image"
    image_1_preview.short_description = 'Clue 1'

    def image_2_preview(self, obj):
        if obj.image_2_url:
            return format_html('<img src="{}" style="height: 60px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />', obj.image_2_url)
        return "No Image"
    image_2_preview.short_description = 'Clue 2'