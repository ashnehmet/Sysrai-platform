"""
AI Script and Storyboard Generator for Sysrai Platform
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

class Character(BaseModel):
    """Character in the film"""
    name: str
    description: str
    age: Optional[str] = None
    personality: str = ""

class Scene(BaseModel):
    """Individual scene in the film"""
    scene_number: int
    duration_seconds: int = 10
    setting: str
    description: str
    dialogue: Optional[str] = None
    camera_angle: str = "medium shot"
    mood: str = "neutral"
    lighting: str = "natural"
    visual_prompt: str = ""

class FilmScript(BaseModel):
    """Complete film script"""
    title: str
    genre: str
    duration_minutes: int
    synopsis: str
    characters: List[Character]
    scenes: List[Scene]
    total_scenes: int
    time_period: str = "modern"
    visual_style: str = "cinematic"

class ScriptGenerator:
    """Generate film scripts from source material"""
    
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-4o-mini",
            temperature=0.7
        )
    
    async def generate_film_script(
        self,
        source_content: str,
        duration_minutes: int = 30,
        genre: str = "drama",
        style: str = "cinematic"
    ) -> FilmScript:
        """Generate complete film script from source material"""
        
        prompt = self._create_script_prompt(
            source_content, duration_minutes, genre, style
        )
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            script_data = json.loads(response.content)
            
            # Parse into FilmScript model
            script = FilmScript(**script_data)
            
            # Generate visual prompts for each scene
            for scene in script.scenes:
                scene.visual_prompt = self._create_visual_prompt(scene, script)
            
            return script
            
        except Exception as e:
            raise Exception(f"Script generation failed: {e}")
    
    def _create_script_prompt(
        self, 
        source_content: str, 
        duration_minutes: int, 
        genre: str, 
        style: str
    ) -> str:
        """Create prompt for script generation"""
        
        scenes_needed = max(3, duration_minutes // 5)  # ~5 minutes per scene
        
        prompt = f"""
        Create a {duration_minutes}-minute {genre} film script in {style} style.
        
        Source Material:
        {source_content[:2000]}
        
        Requirements:
        - Generate exactly {scenes_needed} scenes
        - Each scene should be 5-10 minutes long
        - Include 3-5 main characters with detailed descriptions
        - Ensure visual continuity between scenes
        - Create engaging dialogue for key moments
        - Specify camera angles and visual elements
        - Set in a consistent time period and location
        
        Output as JSON in this exact format:
        {{
            "title": "Film Title",
            "genre": "{genre}",
            "duration_minutes": {duration_minutes},
            "synopsis": "Brief film synopsis",
            "time_period": "e.g., 1940s, modern day, etc.",
            "visual_style": "e.g., noir, bright cinematic, documentary",
            "characters": [
                {{
                    "name": "Character Name",
                    "description": "Detailed physical description and personality",
                    "age": "Age range",
                    "personality": "Personality traits"
                }}
            ],
            "scenes": [
                {{
                    "scene_number": 1,
                    "duration_seconds": 300,
                    "setting": "Detailed location description",
                    "description": "What happens in this scene",
                    "dialogue": "Key dialogue or 'None' if no dialogue",
                    "camera_angle": "wide shot, medium shot, close-up, etc.",
                    "mood": "emotional tone of scene",
                    "lighting": "lighting description",
                    "visual_prompt": "Will be generated separately"
                }}
            ],
            "total_scenes": {scenes_needed}
        }}
        
        Ensure the story has a clear beginning, middle, and end with proper character development.
        """
        
        return prompt
    
    def _create_visual_prompt(self, scene: Scene, script: FilmScript) -> str:
        """Create detailed visual prompt for SkyReels"""
        
        # Base cinematic prompt
        base_prompt = f"FPS-24, professional cinematic {script.visual_style} style"
        
        # Scene specifics
        scene_prompt = f"{scene.description}. {scene.setting}."
        
        # Camera and lighting
        technical = f"{scene.camera_angle}, {scene.lighting} lighting, {scene.mood} mood"
        
        # Characters involved
        characters = []
        for char in script.characters:
            if char.name.lower() in scene.description.lower():
                characters.append(f"{char.name}: {char.description}")
        
        char_prompt = ". ".join(characters) if characters else ""
        
        # Time period consistency
        period_prompt = f"{script.time_period} setting with appropriate costumes and props"
        
        # Combine all elements
        full_prompt = f"{base_prompt}. {scene_prompt} {technical}. {char_prompt}. {period_prompt}. High quality, 9:16 portrait format."
        
        return full_prompt
    
    async def enhance_script_continuity(self, script: FilmScript) -> FilmScript:
        """Enhance script to ensure visual and narrative continuity"""
        
        continuity_prompt = f"""
        Enhance this film script to ensure perfect visual and narrative continuity:
        
        Current Script: {script.json()}
        
        Please:
        1. Ensure all scenes flow logically from one to the next
        2. Maintain consistent character appearances
        3. Keep lighting and mood consistent within acts
        4. Add transition descriptions between scenes
        5. Enhance visual prompts for better SkyReels generation
        6. Ensure time period consistency throughout
        
        Return the enhanced script in the same JSON format.
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=continuity_prompt)])
            enhanced_data = json.loads(response.content)
            return FilmScript(**enhanced_data)
            
        except Exception as e:
            print(f"Warning: Continuity enhancement failed: {e}")
            return script  # Return original if enhancement fails


class StoryboardGenerator:
    """Generate detailed storyboards for film production"""
    
    def __init__(self, script_generator: ScriptGenerator):
        self.script_generator = script_generator
    
    def create_storyboard(self, script: FilmScript) -> List[Dict]:
        """Create detailed storyboard from script"""
        
        storyboard = []
        current_time = 0
        
        for scene in script.scenes:
            # Break scene into shots (typically 3-5 shots per scene)
            shots_per_scene = max(3, scene.duration_seconds // 60)
            shot_duration = scene.duration_seconds // shots_per_scene
            
            for shot in range(shots_per_scene):
                shot_info = {
                    "scene_number": scene.scene_number,
                    "shot_number": shot + 1,
                    "timestamp_start": current_time,
                    "timestamp_end": current_time + shot_duration,
                    "duration": shot_duration,
                    "camera_angle": self._vary_camera_angle(scene.camera_angle, shot),
                    "visual_prompt": scene.visual_prompt,
                    "setting": scene.setting,
                    "mood": scene.mood,
                    "dialogue": scene.dialogue if shot == 0 else None,
                    "transition": "cut" if shot > 0 else "fade in"
                }
                
                storyboard.append(shot_info)
                current_time += shot_duration
        
        return storyboard
    
    def _vary_camera_angle(self, base_angle: str, shot_number: int) -> str:
        """Vary camera angles within a scene for visual interest"""
        
        angle_variations = {
            "wide shot": ["wide shot", "medium wide shot", "wide shot"],
            "medium shot": ["medium shot", "close-up", "over shoulder"],
            "close-up": ["close-up", "extreme close-up", "medium shot"],
            "establishing shot": ["establishing shot", "wide shot", "medium shot"]
        }
        
        variations = angle_variations.get(base_angle, [base_angle])
        return variations[shot_number % len(variations)]


# Utility functions
def load_book_content(file_path: str) -> str:
    """Load content from EPUB or text file"""
    from pathlib import Path
    
    file_path = Path(file_path)
    
    if file_path.suffix.lower() == '.epub':
        # Load EPUB
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
        
        book = epub.read_epub(str(file_path))
        content = []
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                if len(text) > 500:  # Only substantial chapters
                    content.append(text)
        
        return "\n\n".join(content[:5])  # First 5 chapters
        
    else:
        # Load text file
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()[:10000]  # First 10k characters

def save_script_to_file(script: FilmScript, output_path: str):
    """Save script to JSON file"""
    with open(output_path, 'w') as f:
        json.dump(script.dict(), f, indent=2, default=str)
    
    print(f"✅ Script saved to: {output_path}")

def load_script_from_file(file_path: str) -> FilmScript:
    """Load script from JSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    return FilmScript(**data)