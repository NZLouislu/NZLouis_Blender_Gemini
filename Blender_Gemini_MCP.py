# Blender_Gemini_MCP.py

import bpy
import threading
import textwrap
import os
import tempfile
import time
from . import Blender_Gemini_MCP_utils as utils

class GeminiProperties(bpy.types.PropertyGroup):
    prompt: bpy.props.StringProperty(name="Prompt", default="")
    response: bpy.props.StringProperty(name="Response", default="Awaiting prompt...")
    popup_prompt: bpy.props.StringProperty(name="Popup Prompt", default="")
    
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
    include_screenshot: bpy.props.BoolProperty(
        name="Include Screenshot", 
        description="Capture the current 3D Viewport and send it to Gemini", 
        default=False
    )

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
        
        # Screenshot Logic
        image_path = None
        if props.include_screenshot:
            try:
                # Create a temporary path for the screenshot
                temp_dir = tempfile.gettempdir()
                timestamp = int(time.time())
                image_path = os.path.join(temp_dir, f"gemini_screenshot_{timestamp}.png")
                
                # Capture the active 3D view (or current context)
                # We use write_still=True to save it. 
                # Note: This captures the viewport as seen.
                bpy.ops.render.opengl(write_still=True, view_context=True)
                
                # Check where Blender saved it. render.opengl uses render.filepath.
                # We need to temporarily override filepath or move the file?
                # Actually, bpy.ops.render.opengl respects `bpy.context.scene.render.filepath`
                # BETTER APPROACH: Set filepath temporarily
                
                original_filepath = context.scene.render.filepath
                context.scene.render.filepath = image_path
                context.scene.render.image_settings.file_format = 'PNG'
                
                # Capture
                bpy.ops.render.opengl(write_still=True, view_context=False)
                
                # Restore
                context.scene.render.filepath = original_filepath
                
                self.report({'INFO'}, "Screenshot captured.")
                
            except Exception as e:
                self.report({'ERROR'}, f"Screenshot failed: {e}")
                image_path = None # Fallback to text only

        props.response = "Generating response..."
        self._thread_result.clear()

        def threaded_function(api_key, model, prompt, img_path, result_container):
            print("Gemini Thread: Starting request...")
            try:
                response_text = utils.send_prompt_to_gemini(api_key, model, prompt, img_path)
                result_container['result'] = response_text
                print("Gemini Thread: Request successful.")
            except Exception as e:
                error_msg = f"An unexpected error occurred in the thread: {e}"
                result_container['error'] = error_msg
                print(f"Gemini Thread: {error_msg}")
            
            # Clean up temp image
            if img_path and os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except:
                    pass

        self._thread = threading.Thread(target=threaded_function, args=(prefs.api_key, prefs.model_list, prompt_text, image_path, self._thread_result))
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
            except Exception as e:
                error_message = f"Error executing Python code: {e}"
                self.report({'ERROR'}, error_message)
                props.response += f"\n\n--- EXECUTION ERROR ---\n{error_message}"
        else:
            self.report({'WARNING'}, "No Python code block found in the response.")
        
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
        props = context.scene.gemini_properties
        prefs = context.preferences.addons[__package__].preferences
        
        if not prefs.api_key:
            layout.label(text="Please set API Key in Preferences.", icon='ERROR')
            return

        layout.label(text="Enter Prompt:")
        
        # Prompt Input Mode Toggle
        row = layout.row(align=True)
        row.prop(props, "use_text_block_input", toggle=True, text="ABC", icon='FILE_TEXT')
        row.prop(props, "include_screenshot", toggle=True, text="", icon='IMAGE_DATA')
        
        if props.use_text_block_input:
            col = layout.column(align=True)
            col.template_ID(props, "input_text_block", new="text.new", open="text.open")
            if props.input_text_block:
                # Button to edit the text block in a new window/area could be added,
                # but standard UI implies user goes to Text Editor.
                # We can add a small help label.
                col.label(text="Edit in Text Editor", icon='INFO')
        else:
            # Simple Mode
            layout.prop(props, "prompt", text="")

        # Send Button 
        # (Make it prominent)
        row = layout.row()
        row.scale_y = 1.2
        btn_text = "Send Prompt + Screenshot" if props.include_screenshot else "Send Prompt"
        row.operator("gemini.send_prompt", text=btn_text)
        
        layout.separator()
        layout.label(text="Gemini Response:")
        
        box = layout.box()
        col = box.column()

        if props.response:
            wrap_width = max(10, int(context.region.width / 7))
            lines = props.response.split('\n')
            for line in lines:
                wrapped_lines = textwrap.wrap(line, width=wrap_width, replace_whitespace=False)
                if not wrapped_lines:
                    col.label(text="")
                else:
                    for wrapped_line in wrapped_lines:
                        col.label(text=wrapped_line)
        
        if "```python" in props.response:
            layout.operator("gemini.execute_code", icon='PLAY')
