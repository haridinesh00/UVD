import random
import requests
from pydantic import BaseModel, Field
from google import genai
from django.conf import settings
from celery import shared_task
from .models import PuzzleLevel

# 1. NEW SCHEMA: Now asks Gemini for a Category and a Hint
class RebusPuzzle(BaseModel):
    final_answer: str = Field(description="The compound word or famous phrase (e.g., 'Bill Gates')")
    reasoning: str = Field(description="Explain why the two visual clues are unambiguous NOUNS, not adjectives.")
    category: str = Field(description="A short, 1-2 word category for the UI (e.g., 'Geography', 'Movie', 'Tech')")
    hint: str = Field(description="A helpful textual hint for the player (e.g., 'A famous wizard with a scar')")
    search_term_1: str = Field(description="A highly specific, single concrete NOUN.")
    search_term_2: str = Field(description="A highly specific, single concrete NOUN.")

class PuzzleList(BaseModel):
    puzzles: list[RebusPuzzle]

@shared_task
def generate_new_levels(num_levels=5):
    """
    Calls Gemini to generate advanced puzzle concepts, fetches Unsplash images, 
    and saves the complete levels to the database.
    """
    print(f"🧠 Asking Gemini to generate {num_levels} new ADVANCED puzzles...")
    
    recent_levels = PuzzleLevel.objects.order_by('-level_number')[:50]
    used_answers = [level.correct_answer.lower() for level in recent_levels]
    used_answers_str = ", ".join(used_answers) if used_answers else "None"

    themes = [
        "World Geography and Famous Landmarks",
        "Historical Events and Famous Historical Figures",
        "General Science, Astronomy, and Nature Concepts",
        "General Pop Culture and Blockbuster Movies",
        # "Complex Compound Words"
    ]
    selected_theme = random.choice(themes)
    print(f"🎲 Selected Theme for this batch: {selected_theme}")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    prompt = f"""
    You are an expert puzzle designer making highly difficult, clever Rebus visual puzzles.
    Generate {num_levels} puzzles strictly based on this theme: {selected_theme}.
    
    CRITICAL RULES FOR STOCK PHOTOGRAPHY:
    1. NO ADJECTIVES OR ABSTRACT CONCEPTS. Do not use words like 'hairy', 'fast', 'cold'.
    2. USE CONCRETE, UNAMBIGUOUS NOUNS ONLY. If you want 'hair', search for 'hair comb'.
    3. SINGLE SUBJECT FOCUS. The object must be easily recognizable as the main subject of a photo.
    4. DO NOT generate ANY of these previously used answers: {used_answers_str}.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': PuzzleList,
            'temperature': 0.9 
        }
    )
    
    puzzle_data = response.parsed
    
    for item in puzzle_data.puzzles:
        print(f"\n🔍 Fetching images for: {item.final_answer}")
        print(f"   Reasoning: {item.reasoning}")
        print(f"   Clues: {item.search_term_1} + {item.search_term_2}")
        
        img1_url = fetch_unsplash_image(item.search_term_1)
        img2_url = fetch_unsplash_image(item.search_term_2)
        
        if img1_url and img2_url:
            last_level = PuzzleLevel.objects.order_by('-level_number').first()
            new_level_num = (last_level.level_number + 1) if last_level else 1
            
            PuzzleLevel.objects.create(
                level_number=new_level_num,
                image_1_url=img1_url, 
                image_2_url=img2_url,
                correct_answer=item.final_answer,
                category=item.category, # SAVING THE NEW DATA
                hint=item.hint          # SAVING THE NEW DATA
            )
            print(f"✅ Successfully generated and saved level {new_level_num}!")
        else:
            print(f"❌ Failed to find good stock images for {item.final_answer}. Skipping.")

def fetch_unsplash_image(query):
    """
    Hits the Unsplash API and returns the URL for the first 'regular' sized image result.
    Injects hidden keywords to force clean, uncluttered photos.
    """
    api_key = settings.UNSPLASH_API_KEY 
    optimized_query = f"{query} minimalist isolated single object"
    url = f"https://api.unsplash.com/search/photos?query={optimized_query}&per_page=1&content_filter=high"
    headers = {"Authorization": f"Client-ID {api_key}"}
    
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status() 
        data = res.json()
        if data.get('results') and len(data['results']) > 0:
            return data['results'][0]['urls']['regular']
    except Exception as e:
        print(f"Error fetching image for '{query}': {e}")
    return None