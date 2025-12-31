# Blender_Gemini_MCP_utils.py

import re
import os
import sys
import site

# Try to add user site-packages to path (fixes "library not found" if installed without Admin rights)
try:
    user_site_pkg = site.getusersitepackages()
    if user_site_pkg not in sys.path:
        sys.path.append(user_site_pkg)
except Exception:
    pass

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from PIL import Image
except ImportError:
    Image = None

SYSTEM_PROMPT = """You are an expert Blender Python automation assistant.
YOUR GOAL: Generate executable 'bpy' Python scripts to fulfill the user's request.

CRITICAL RULES:
1. **NO CHATTER**: Do not output conversational text like "Here is the code" or "To use this script...".
2. **CODE ONLY**: Your entire response should be a SINGLE markdown code block (```python ... ```).
3. **COMMENTS**: Put all explanations, warnings, and instructions INSIDE the code as Python comments (#).
4. **SELF-CONTAINED**: The code must handle imports (import bpy, bmesh, math) and context setup.
5. **ROBUSTNESS**: Check if objects exist before operating on them. Use try-except blocks/poll methods where appropriate.
6. **NO MAIN BLOCK**: Do NOT use `if __name__ == "__main__":`. Call functions directly at the end or write top-level code.

EXAMPLE FORMAT:
```python
import bpy

def create_stuff():
    bpy.ops.mesh.primitive_cube_add()

# Call the function directly!
create_stuff()
```"""

def load_api_key_from_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('GEMINI_API_KEY='):
                        api_key = line.split('=', 1)[1].strip().strip('\'"')
                        if api_key:
                            print(f"Loaded API key from .env file")
                            return api_key
        except Exception as e:
            print(f"Error reading .env file: {e}")
    return None

def test_api_connection(api_key):
    if not genai:
        return (False, "google-generativeai library not installed")
    
    if not api_key:
        return (False, "API key is empty")
    
    try:
        genai.configure(api_key=api_key)
        models = list(genai.list_models())
        
        if not models:
            return (False, "No models available with this API key")
        
        gemini_models = [m for m in models if 'gemini' in m.name.lower() and 'generateContent' in m.supported_generation_methods]
        
        if not gemini_models:
            return (False, "No Gemini models found")

        # Sort to show the newest/best models in the message
        gemini_models.sort(key=lambda x: (
            '3' not in x.name and '3.0' not in x.name,
            '2.5' not in x.name,
            '2.0' not in x.name,
            x.name
        ))
        
        model_names = [m.name for m in gemini_models[:3]]
        return (True, f"Connection successful! Found {len(gemini_models)} models: {', '.join(model_names)}...")
        
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            return (False, "Invalid API key")
        elif "quota" in error_msg.lower():
            return (False, "API quota exceeded")
        elif "permission" in error_msg.lower():
            return (False, "Permission denied - check API key permissions")
        else:
            return (False, f"Connection failed: {error_msg}")


def get_available_models(api_key):
    if not genai:
        return []
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Strictly filter models based on user request (Clean List)
        # Keep: 3.x, 2.5 Flash/Pro, 2.0 Flash/Pro
        # Exclude: Lite, Image, TTS, specific versions (001, 002) if aliases exist
        
        filtered_models = []
        for m in models:
            name_lower = m.name.lower()
            
            # Must be a Gemini model
            if 'gemini' not in name_lower:
                continue
            
            # Must be one of the core generations
            if not any(v in name_lower for v in ['gemini-3', 'gemini-2.5', 'gemini-2.0']):
                continue
                
            # Exclude unwanted variations
            if any(x in name_lower for x in ['lite', 'image', 'audio', 'tts', 'tuning', 'legacy']):
                continue
            
            # Filter out specific dated versions if they create clutter (e.g. 001, 002)
            # We prefer names like "gemini-1.5-flash" over "gemini-1.5-flash-001"
            # But for 3.0 preview we keep it.
            if re.search(r'-\d{3}$', m.name): # Ends in -001, -002 etc
                continue
                
            filtered_models.append(m)

        # Sort: 3.0 -> 2.5 -> 2.0 (Pro then Flash)
        filtered_models.sort(key=lambda x: (
            '3' not in x.name and '3.0' not in x.name, # 3.0 First
            '2.5' not in x.name,                       # then 2.5
            '2.0' not in x.name,                       # then 2.0
            'pro' not in x.name.lower(),               # Pro before Flash? Or Flash before Pro? 
                                                       # Usually Flash is default, but Pro is stronger. 
                                                       # Let's group by version, then alphabetical.
             x.name
        ))
        
        # Format for Blender Enum: (identifier, name, description)
        return [(m.name, m.name.replace("models/", "").replace("-", " ").title(), "") for m in filtered_models]
    
    except Exception as e:
        print(f"Could not fetch models: {e}")
        return []

def send_prompt_to_gemini(api_key, model_name, prompt_text, image_path=None):
    """
    Sends a prompt to the specified Gemini model.
    Supports text-only or text+image (multimodal) if an image_path is provided.
    """
    if not genai:
        return "Error: 'google-generativeai' library not installed."
        
    try:
        genai.configure(api_key=api_key)
        # model_name now correctly contains the "models/" prefix.
        model = genai.GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)
        
        content = [prompt_text]
        
        if image_path:
            if not Image:
                return "Error: 'Pillow' (PIL) library not installed, cannot process images."
            try:
                img = Image.open(image_path)
                content.append(img)
            except Exception as img_err:
                return f"Error loading image: {img_err}"

        response = model.generate_content(content)
        return response.text
    except Exception as e:
        # Return the actual error from the API for better debugging.
        return f"An API error occurred: {e}"

def extract_python_code(text):
    """Extracts code from a ```python ... ``` block."""
    match = re.search(r'```python\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None
