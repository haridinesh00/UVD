import random
import time
import requests
from pydantic import BaseModel, Field
from google import genai
from django.conf import settings
from celery import shared_task
from .models import PuzzleLevel

# 1. Update Schema for Wikipedia
class RebusPuzzle(BaseModel):
    final_answer: str = Field(description="The compound word or famous phrase (e.g., 'Bill Gates')")
    reasoning: str = Field(description="Explain why the two visual clues are unambiguous NOUNS, not adjectives.")
    category: str = Field(description="A short, 1-2 word category for the UI")
    hint: str = Field(description="A helpful textual hint for the player")
    search_term_1: str = Field(description="A specific Wikipedia article title (e.g., 'Apple', 'Taj Mahal').")
    search_term_2: str = Field(description="A specific Wikipedia article title (e.g., 'Tree', 'George Washington').")

class PuzzleList(BaseModel):
    puzzles: list[RebusPuzzle]

@shared_task
def generate_new_levels(num_levels=5):
    print(f"🧠 Asking Gemini to generate {num_levels} new ADVANCED puzzles...")
    
    recent_levels = PuzzleLevel.objects.order_by('-level_number')[:50]
    used_answers = [level.correct_answer.lower() for level in recent_levels]
    used_answers_str = ", ".join(used_answers) if used_answers else "None"

    themes = [
        "World Geography and Landmarks",
        "Historical Events and Figures",
        "Pop Culture and Blockbuster Movies",
        "Retro Video Games",
        "Malayalam Cinema",
        "Complex Compound Words"
        "Famous brands"
    ]
    selected_theme = random.choice(themes)
    
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # 2. Update Prompt for Wikipedia
    prompt = f"""
    You are an expert puzzle designer making highly difficult, clever Rebus visual puzzles.
    Generate {num_levels} puzzles strictly based on this theme: {selected_theme}.
    
    CRITICAL RULES:
    1. We are using the Wikipedia API to fetch images. 
    2. Your search_term_1 and search_term_2 MUST be exact, literal Wikipedia article titles (e.g., 'Lego', 'Rubik\\'s Cube', 'Mohanlal'). Do not use generic descriptive sentences.
    3. DO NOT generate ANY of these previously used answers: {used_answers_str}.
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
        print(f"\n🔍 Fetching Wikipedia images for: {item.final_answer}")
        
        # 3. THE FIX: Pass only ONE argument. No more ddg_client!
        img1_url = fetch_image(item.search_term_1)
        time.sleep(1) # A polite 1-second delay for Wikipedia's servers
        
        img2_url = fetch_image(item.search_term_2)
        time.sleep(1)
        
        if img1_url and img2_url:
            last_level = PuzzleLevel.objects.order_by('-level_number').first()
            new_level_num = (last_level.level_number + 1) if last_level else 1
            
            PuzzleLevel.objects.create(
                level_number=new_level_num,
                image_1_url=img1_url, 
                image_2_url=img2_url,
                correct_answer=item.final_answer,
                category=item.category,
                hint=item.hint
            )
            print(f"✅ Successfully generated and saved level {new_level_num}!")
        else:
            print(f"❌ Failed to fetch images for {item.final_answer}. Skipping.")

def fetch_image(query):
    """
    Fetches the main image for a Wikipedia article.
    Includes a User-Agent header to bypass Wikipedia's bot-blocker.
    """
    # 1. THE FIX: Create a polite caller ID for Wikipedia
    headers = {
        'User-Agent': 'RebuxGameBot/1.0 (Educational Rebus Game Backend)'
    }
    
    search_url = "https://en.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "utf8": 1,
        "srlimit": 1
    }
    
    try:
        # Pass the headers into the first request
        search_res = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        
        # If Wikipedia still rejects us, print the exact reason instead of crashing
        if search_res.status_code != 200:
            print(f"Wikipedia rejected search for '{query}': {search_res.status_code}")
            return None
            
        search_data = search_res.json()
        
        if not search_data.get('query', {}).get('search'):
            return None
            
        title = search_data['query']['search'][0]['title']
        
        image_url = f"https://en.wikipedia.org/w/api.php"
        image_params = {
            "action": "query",
            "format": "json",
            "prop": "pageimages",
            "titles": title,
            "pithumbsize": 800
        }
        
        # Pass the headers into the second request too!
        img_res = requests.get(image_url, params=image_params, headers=headers, timeout=10)
        img_data = img_res.json()
        
        pages = img_data.get('query', {}).get('pages', {})
        
        for page_id, page_data in pages.items():
            if 'thumbnail' in page_data:
                return page_data['thumbnail']['source']
                
    except Exception as e:
        print(f"Wikipedia fetch error for '{query}': {e}")
        
    return None