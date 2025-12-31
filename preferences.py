# preferences.py

import bpy
from . import Blender_Gemini_MCP_utils as utils

_model_list_cache = [
    ("gemini-3-flash-preview", "Gemini 3 Flash Preview", "Latest Gemini 3.0 model"),
    ("gemini-2.5-flash", "Gemini 2.5 Flash", "Fast and efficient"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro", "Advanced reasoning"),
    ("gemini-2.0-flash-exp", "Gemini 2.0 Flash Exp", "Stable fallback"),
]

def get_models_for_enum(self, context):
    global _model_list_cache
    return _model_list_cache

def refresh_models_background(api_key):
    print("Refreshing Gemini models...")
    global _model_list_cache
    models = utils.get_available_models(api_key)
    if models:
        _model_list_cache = models
        print(f"Models found: {[m[0] for m in models]}")
    else:
        _model_list_cache = [("gemini-3-flash-preview", "No models found (check API Key)", "")]
        print("No models found or API key is invalid.")
    
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'PREFERENCES':
                area.tag_redraw()

def update_model_list_on_apikey_change(self, context):
    prefs = context.preferences.addons[__package__].preferences
    if prefs.api_key:
        bpy.app.timers.register(lambda: refresh_models_background(prefs.api_key))
    return None

class GeminiAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    api_key: bpy.props.StringProperty(
        name="Gemini API Key",
        description="Paste your Google Gemini API key here",
        subtype='PASSWORD',
        update=update_model_list_on_apikey_change,
    )

    model_list: bpy.props.EnumProperty(
        name="Model",
        description="Select the Gemini model to use",
        items=get_models_for_enum,
    )
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row(align=True)
        row.prop(self, "api_key")
        
        # Test Connection Button
        row.operator("gemini.test_connection", text="", icon='CHECKMARK')
        
        row = layout.row()
        row.prop(self, "model_list")
        row.operator("gemini.refresh_models", text="", icon='FILE_REFRESH')

class GEMINI_OT_test_connection(bpy.types.Operator):
    bl_idname = "gemini.test_connection"
    bl_label = "Test API Connection"
    bl_description = "Test connection to Gemini API (loads from .env if key is empty)"
    
    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        api_key = prefs.api_key
        
        # Try loading from .env if empty
        if not api_key:
            env_key = utils.load_api_key_from_env()
            if env_key:
                prefs.api_key = env_key
                api_key = env_key
                self.report({'INFO'}, "API Key loaded from .env file")
            else:
                self.report({'WARNING'}, "No API Key found in preferences or .env file")
                return {'CANCELLED'}

        success, message = utils.test_api_connection(api_key)
        
        if success:
            self.report({'INFO'}, message)
            # Auto-refresh models if connection is good
            refresh_models_background(api_key)
        else:
            self.report({'ERROR'}, message)
            
        return {'FINISHED'}

class GEMINI_OT_refresh_models(bpy.types.Operator):
    bl_idname = "gemini.refresh_models"
    bl_label = "Refresh Model List"
    
    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        api_key = prefs.api_key
        
        # Also try .env here
        if not api_key:
            env_key = utils.load_api_key_from_env()
            if env_key:
                prefs.api_key = env_key
                api_key = env_key
                self.report({'INFO'}, "API Key loaded from .env file")
        
        if api_key:
            refresh_models_background(api_key)
            self.report({'INFO'}, "Model list refreshed.")
        else:
            self.report({'WARNING'}, "Please enter an API key first.")
        return {'FINISHED'}
