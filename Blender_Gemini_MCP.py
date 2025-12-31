# Blender_Gemini_MCP.py

import bpy
import threading
import textwrap
import os
import tempfile
import time
from . import Blender_Gemini_MCP_utils as utils
from bpy.props import StringProperty, BoolProperty, PointerProperty, CollectionProperty

# PropertyGroup for Image Attachments
class GeminiImageItem(bpy.types.PropertyGroup):
    filepath: StringProperty(name="File Path")
    name: StringProperty(name="Name")

class GeminiProperties(bpy.types.PropertyGroup):
    prompt: bpy.props.StringProperty(name="Prompt", default="")
    response: bpy.props.StringProperty(name="Response", default="Awaiting prompt...")
    popup_prompt: bpy.props.StringProperty(name="Popup Prompt", default="")
    
    # Image Attachments Collection
    images: CollectionProperty(type=GeminiImageItem)
    
    # New properties for enhanced UX
    use_text_block_input: bpy.props.BoolProperty(
        name="Use Text Block", 
        description="Use a Text Block for multi-line prompts", 
        default=False
    )
    input_text_block: bpy.props.PointerProperty(
        name="Input Text", 
        type=bpy.types.Text
    )
    
    last_error: bpy.props.StringProperty(
        name="Last Error",
        default=""
    )
    last_failed_code: bpy.props.StringProperty(
        name="Last Failed Code",
        default=""
    )

class GEMINI_OT_add_image(bpy.types.Operator):
    bl_label = "Add Image"
    bl_idname = "gemini.add_image"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        if self.filepath:
            item = context.scene.gemini_properties.images.add()
            item.filepath = self.filepath
            item.name = os.path.basename(self.filepath)
            self.report({'INFO'}, f"Added image: {item.name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class GEMINI_OT_paste_image(bpy.types.Operator):
    bl_label = "Paste Image"
    bl_idname = "gemini.paste_image"
    bl_description = "Paste image from clipboard"

    def execute(self, context):
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        filename = f"gemini_paste_{timestamp}.png"
        filepath = os.path.join(temp_dir, filename)
        
        if utils.get_clipboard_image(filepath):
            item = context.scene.gemini_properties.images.add()
            item.filepath = filepath
            item.name = "Clipboard Image"
            self.report({'INFO'}, "Image pasted from clipboard")
        else:
            self.report({'WARNING'}, "No image found in clipboard")
        
        return {'FINISHED'}

class GEMINI_OT_remove_image(bpy.types.Operator):
    bl_label = "Remove Image"
    bl_idname = "gemini.remove_image"
    
    index: bpy.props.IntProperty()

    def execute(self, context):
        props = context.scene.gemini_properties
        props.images.remove(self.index)
        return {'FINISHED'}

class GEMINI_OT_capture_screenshot(bpy.types.Operator):
    bl_label = "Capture Screenshot"
    bl_idname = "gemini.capture_screenshot"
    bl_description = "Capture current viewport screenshot"

    def execute(self, context):
        try:
            temp_dir = tempfile.gettempdir()
            timestamp = int(time.time())
            filename = f"gemini_screen_{timestamp}.png"
            image_path = os.path.join(temp_dir, filename)
            
            original_filepath = context.scene.render.filepath
            context.scene.render.filepath = image_path
            context.scene.render.image_settings.file_format = 'PNG'
            
            bpy.ops.render.opengl(write_still=True, view_context=False)
            
            context.scene.render.filepath = original_filepath
            
            item = context.scene.gemini_properties.images.add()
            item.filepath = image_path
            item.name = "Screenshot"
            self.report({'INFO'}, "Screenshot captured")
            
        except Exception as e:
            self.report({'ERROR'}, f"Screenshot failed: {e}")
            
        return {'FINISHED'}

class GEMINI_OT_open_text_editor(bpy.types.Operator):
    bl_label = "Open Multi-line Editor"
    bl_idname = "gemini.open_text_editor"
    bl_description = "Open a floating Text Editor for multi-line prompts (Ctrl+Enter to new line)"

    def execute(self, context):
        props = context.scene.gemini_properties
        
        # Ensure a text block exists
        if not props.input_text_block:
            if "Gemini Prompt" in bpy.data.texts:
                props.input_text_block = bpy.data.texts["Gemini Prompt"]
            else:
                props.input_text_block = bpy.data.texts.new("Gemini Prompt")
        
        # Open a new window with the Text Editor
        # We use a slight hack: duplicate the current area into a new window, then switch it.
        # OR simpler: bpy.ops.screen.userpref_show() is for prefs.
        # bpy.ops.wm.window_new() creates a new window.
        
        bpy.ops.wm.window_new()
        new_window = context.window_manager.windows[-1]
        area = new_window.screen.areas[0]
        area.ui_type = 'TEXT_EDITOR'
        
        # Set the text space to use our text block
        for space in area.spaces:
            if space.type == 'TEXT_EDITOR':
                space.text = props.input_text_block
                # Optional: Enable syntax highlight or wrapping
                space.show_word_wrap = True
                space.show_line_numbers = True
        
        return {'FINISHED'}

# Menu for the Image Button
class GEMINI_MT_image_menu(bpy.types.Menu):
    bl_label = "Add Image"
    bl_idname = "GEMINI_MT_image_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("gemini.add_image", text="Upload Image", icon='FILE_FOLDER')
        layout.operator("gemini.paste_image", text="Paste from Clipboard", icon='PASTE_DOWN')
        layout.operator("gemini.capture_screenshot", text="Capture Screenshot", icon='SCREEN_BACK')


class GEMINI_OT_send_prompt(bpy.types.Operator):
    bl_label = "Send Prompt"
    bl_idname = "gemini.send_prompt"
    
    from_popup: bpy.props.BoolProperty(default=False)
    _timer = None
    _thread = None
    _thread_result = {}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        props = context.scene.gemini_properties

        if not prefs.api_key:
            self.report({'ERROR'}, "Please set your Gemini API Key in the addon preferences.")
            return {'CANCELLED'}
        
        # Determine Prompt Source
        prompt_text = ""
        if self.from_popup:
            prompt_text = props.popup_prompt
        elif props.use_text_block_input:
            if props.input_text_block:
                # Read all lines from the text block
                prompt_text = props.input_text_block.as_string()
            else:
                self.report({'WARNING'}, "No Text Block selected.")
                return {'CANCELLED'}
        else:
            prompt_text = props.prompt

        if not prompt_text.strip():
            self.report({'INFO'}, "Prompt is empty.")
            return {'CANCELLED'}
        
        # Prepare Image Paths
        final_image_paths = []
        for img in props.images:
            final_image_paths.append(img.filepath)

        props.response = "Generating response..."
        self._thread_result.clear()

        def threaded_function(api_key, model, prompt, img_paths, result_container):
            print("Gemini Thread: Starting request...")
            try:
                response_text = utils.send_prompt_to_gemini(api_key, model, prompt, img_paths)
                result_container['result'] = response_text
                print("Gemini Thread: Request successful.")
            except Exception as e:
                error_msg = f"An unexpected error occurred in the thread: {e}"
                result_container['error'] = error_msg
                print(f"Gemini Thread: {error_msg}")
            
            # Note: We do NOT delete images here automatically as user might want to drag/drop multiple times.
            # But users might expect temp screenshots to go away. 
            # For this version, we keeping them is safer.

        self._thread = threading.Thread(target=threaded_function, args=(prefs.api_key, prefs.model_list, prompt_text, final_image_paths, self._thread_result))
        self._thread.start()

        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)
        
        if self.from_popup:
            props.popup_prompt = ""

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if not self._thread.is_alive():
                props = context.scene.gemini_properties
                if 'error' in self._thread_result:
                    props.response = self._thread_result['error']
                elif 'result' in self._thread_result:
                    props.response = self._thread_result['result']
                else:
                    props.response = "Task finished, but no result was returned. Check the console."
                
                # --- CORRECTION ---
                # Force all UI regions to update to show the new response immediately,
                # without needing a mouse move.
                for window in context.window_manager.windows:
                    for area in window.screen.areas:
                        area.tag_redraw()

                context.window_manager.event_timer_remove(self._timer)
                return {'FINISHED'}
        
        # Allow other events to pass through while waiting
        return {'PASS_THROUGH'}

class GEMINI_OT_execute_code(bpy.types.Operator):
    bl_label = "Execute Code"
    bl_idname = "gemini.execute_code"

    def execute(self, context):
        props = context.scene.gemini_properties
        code_to_run = utils.extract_python_code(props.response)

        if code_to_run:
            try:
                exec(code_to_run, {'bpy': bpy})
                self.report({'INFO'}, "Code executed successfully.")
                # Clear error state on success
                props.last_error = ""
                props.last_failed_code = ""
            except Exception as e:
                error_message = f"Error: {str(e)}"
                self.report({'ERROR'}, error_message)
                
                # Store error context for potential retry
                props.last_error = str(e)
                props.last_failed_code = code_to_run
                
                # Append error to response for visibility
                props.response += f"\n\n--- EXECUTION ERROR ---\n{error_message}\n\nTip: This may be a version compatibility issue. Try asking Gemini to fix the error."
        else:
            self.report({'WARNING'}, "No Python code block found in the response.")
        
        return {'FINISHED'}

class GEMINI_OT_fix_error(bpy.types.Operator):
    bl_label = "Ask Gemini to Fix Error"
    bl_idname = "gemini.fix_error"
    bl_description = "Send error details to Gemini and ask for a corrected version"

    def execute(self, context):
        props = context.scene.gemini_properties
        
        if not props.last_error:
            self.report({'WARNING'}, "No error to fix.")
            return {'CANCELLED'}
        
        # Construct a fix request prompt
        fix_prompt = f"""The previous code caused this error:

ERROR: {props.last_error}

FAILED CODE:
```python
{props.last_failed_code}
```

Please provide a CORRECTED version that fixes this error. Remember:
- Use only APIs compatible with Blender {utils.get_blender_version()}
- Available render engines: BLENDER_EEVEE, BLENDER_WORKBENCH, CYCLES
- Return ONLY the corrected ```python code block```"""
        
        # Set the prompt and trigger send
        props.prompt = fix_prompt
        bpy.ops.gemini.send_prompt('EXEC_DEFAULT')
        
        self.report({'INFO'}, "Asking Gemini to fix the error...")
        return {'FINISHED'}

class GEMINI_OT_popup_window(bpy.types.Operator):
    bl_label = "Gemini Prompt"
    bl_idname = "gemini.popup_window"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        props = context.scene.gemini_properties
        layout.prop(props, "popup_prompt", text="")

    def execute(self, context):
        bpy.ops.gemini.send_prompt('EXEC_DEFAULT', from_popup=True)
        return {'FINISHED'}

class GEMINI_PT_panel(bpy.types.Panel):
    bl_label = "Gemini AI Assistant"
    bl_idname = "GEMINI_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gemini AI'

    def draw(self, context):
        layout = self.layout
        try:
            props = context.scene.gemini_properties
            # Safe preference access
            addon_prefs = context.preferences.addons.get(__package__)
            prefs = addon_prefs.preferences if addon_prefs else None
            
            if not prefs or not prefs.api_key:
                layout.label(text="Please set API Key in Preferences.", icon='ERROR')
                return

            # --- Attachments List ---
            if props.images:
                box = layout.box()
                box.label(text="Attachments:", icon='FILE')
                row = box.row()
                
                # Simple list of chips
                flow = box.grid_flow(row_major=True, columns=0, even_columns=False, even_rows=False, align=True)
                for i, img in enumerate(props.images):
                    row = flow.row(align=True)
                    row.label(text=img.name, icon='IMAGE_DATA')
                    op = row.operator("gemini.remove_image", text="", icon='X')
                    op.index = i

            # --- Main Chat Input Area ---
            layout.label(text="Deepmind Agent:")
            
            box = layout.box()
            row = box.row(align=True)
            
            # 1. Left: Image Button (Menu)
            row.menu("GEMINI_MT_image_menu", text="", icon='IMAGE_DATA')
            
            # 2. Center: Input
            sub = row.row(align=True)
            
            # Restore Height for "Textarea" feel (Requested by User)
            # Note: StringProperty is single-line only. For multi-line, use Text Block mode.
            if not props.use_text_block_input:
                sub.scale_y = 1.5 
            
            if props.use_text_block_input:
                 sub.template_ID(props, "input_text_block", new="text.new", open="text.open")
                 sub.operator("gemini.open_text_editor", text="", icon='OPTIONS')
            else:
                 sub.prop(props, "prompt", text="")
            
            # 3. Right: Send Button
            sub_btn = row.row(align=True)
            if not props.use_text_block_input:
                sub_btn.scale_y = 1.5 # Match input height
                
            sub_btn.operator("gemini.send_prompt", text="", icon='PLAY')
            
            # Text Block Toggle
            row_opt = layout.row(align=True)
            row_opt.prop(props, "use_text_block_input", toggle=True, text="Use Multi-line Text Block", icon='FILE_TEXT')
            
            # If showing text block, give a big helper button
            if props.use_text_block_input:
                row_helper = layout.row()
                row_helper.operator("gemini.open_text_editor", text="Open Multi-line Editor (Ctrl+Enter)", icon='TEXT')

            layout.separator()
            layout.label(text="Gemini Response:")
            
            box = layout.box()
            col = box.column()

            if props.response:
                # Ensure we have a valid context region width for wrapping
                region_width = context.region.width if context.region else 300
                wrap_width = max(20, int(region_width / 7)) # Adjust divisor as needed
                
                lines = props.response.split('\n')
                for line in lines:
                    wrapped_lines = textwrap.wrap(line, width=wrap_width, replace_whitespace=False)
                    if not wrapped_lines:
                        col.label(text="")
                    else:
                        for wrapped_line in wrapped_lines:
                            col.label(text=wrapped_line)
            else:
                col.label(text="Awaiting prompt...")
            
            # Action buttons for code execution
            if "```python" in props.response:
                row = layout.row(align=True)
                row.operator("gemini.execute_code", icon='PLAY', text="Execute Code")
                
                # Show 'Fix Error' button if there was an execution error
                if props.last_error:
                    row.operator("gemini.fix_error", icon='FILE_REFRESH', text="Fix Error")

        except Exception as e:
            layout.label(text="UI Error: Check Console", icon='ERROR')
            print(f"UI Error: {e}")
