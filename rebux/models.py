from django.db import models
from django.contrib.auth.models import User

class PuzzleLevel(models.Model):
    level_number = models.IntegerField(unique=True)
    
    # Using URLFields instead of ImageFields to store the Unsplash links directly
    image_1_url = models.URLField(max_length=1000)
    image_2_url = models.URLField(max_length=1000)
    
    # Optional extra images (in case you want 3-pic or 4-pic puzzles later)
    image_3_url = models.URLField(max_length=1000, blank=True, null=True)
    image_4_url = models.URLField(max_length=1000, blank=True, null=True)
    
    correct_answer = models.CharField(max_length=100)
    
    # NEW FIELDS
    category = models.CharField(max_length=50, default="General")
    hint = models.CharField(max_length=255, default="Keep thinking!")
    
    def check_answer(self, guess):
        """
        Strips spaces and makes everything lowercase so the player isn't
        punished for bad formatting (e.g., 'BillGates' vs 'bill gates').
        """
        clean_guess = guess.lower().replace(" ", "")
        clean_answer = self.correct_answer.lower().replace(" ", "")
        return clean_guess == clean_answer

    def __str__(self):
        return f"Level {self.level_number}: {self.correct_answer}"

class PlayerProfile(models.Model):
    """
    Tracks the user's current level and score.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    current_level = models.IntegerField(default=1)
    score = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - Level {self.current_level}"