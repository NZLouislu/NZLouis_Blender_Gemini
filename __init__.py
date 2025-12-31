# __init__.py

bl_info = {
    "name": "Gemini AI Assistant",
    "author": "Louis (based on Gabriel Netto's original addon)",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Gemini AI",
    "description": "Control Blender with Gemini 3.0 Flash. Optimized for AI digital twins workflows.",
    "warning": "",
    "doc_url": "https://github.com/nzlouis/blender-gemini-assistant",
    "category": "3D View",
}

import bpy
from bpy.props import PointerProperty
from . import Blender_Gemini_MCP
from . import Blender_Gemini_MCP_utils
from . import preferences

import importlib
importlib.reload(Blender_Gemini_MCP)
importlib.reload(Blender_Gemini_MCP_utils)
importlib.reload(preferences)

addon_keymaps = []

classes = (
    Blender_Gemini_MCP.GeminiImageItem,  # Must be before Properties
    Blender_Gemini_MCP.GEMINI_MT_image_menu,
    Blender_Gemini_MCP.GEMINI_OT_add_image,
    Blender_Gemini_MCP.GEMINI_OT_paste_image,
    Blender_Gemini_MCP.GEMINI_OT_remove_image,
    Blender_Gemini_MCP.GEMINI_OT_capture_screenshot,
    Blender_Gemini_MCP.GeminiProperties,
    Blender_Gemini_MCP.GEMINI_OT_send_prompt,
    Blender_Gemini_MCP.GEMINI_OT_execute_code,
    Blender_Gemini_MCP.GEMINI_OT_popup_window,
    Blender_Gemini_MCP.GEMINI_PT_panel,
    preferences.GeminiAddonPreferences,
    preferences.GEMINI_OT_refresh_models,
    preferences.GEMINI_OT_test_connection,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.gemini_properties = PointerProperty(type=Blender_Gemini_MCP.GeminiProperties)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(Blender_Gemini_MCP.GEMINI_OT_popup_window.bl_idname, 'G', 'PRESS', alt=True)
        addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.Scene.gemini_properties