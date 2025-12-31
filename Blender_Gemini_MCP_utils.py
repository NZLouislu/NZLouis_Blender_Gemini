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

SYSTEM_PROMPT = """You are an expert Blender 3D modeling assistant with deep knowledge of Blender's Python API (bpy).

When generating Python code for Blender:
1. Ensure code is correct, efficient, and ready for immediate execution
2. Always wrap Python code in ```python ... ``` blocks
3. Use proper error handling where appropriate
4. Include selection and scene context management
5. Optimize for performance and best practices
6. Consider Blender version compatibility (2.80+)

The user is working in Blender with the 'bpy' module available. Provide clear, actionable responses focused on 3D modeling, animation, materials, and scene management."""

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
        
        model_names = [m.name for m in gemini_models[:3]]
        return (True, f"Connection successful! Found {len(gemini_models)} models: {', '.join(model_names)}")
        
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
        
        gemini_models = [model for model in models if 'gemini' in model.lower()]
        
        gemini_models_sorted = sorted(gemini_models, key=lambda x: (
            '3' not in x and '3.0' not in x,
            '2.0' not in x,
            'flash' not in x.lower(),
            'pro' not in x.lower(),
            x
        ))
        
        return [(model, model.replace("models/", "").replace("-"," ").title(), "") for model in gemini_models_sorted]
    
    except Exception as e:
        print(f"Could not fetch models: {e}")
        return []

def send_prompt_to_gemini(api_key, model_name, prompt_text):
    """Sends a prompt to the specified Gemini model with a system instruction."""
    if not genai:
        return "Error: 'google-generativeai' library not installed."
        
    try:
        genai.configure(api_key=api_key)
        # model_name now correctly contains the "models/" prefix.
        model = genai.GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)
        response = model.generate_content(prompt_text)
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
