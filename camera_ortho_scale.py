from typing import Optional

import bpy
import rna_keymap_ui
from bpy.types import Object
from mathutils import Matrix


bl_info = {
    "name": "Orthographic Scale",
    "author": "MarshmallowCirno",
    "version": (1, 0),
    "blender": (3, 3, 1),
    "location": "Shortcut in the addon preferences ",
    "description": "Adjust camera orthographic scale while focusing on the 3D cursor",
    "warning": "",
    "doc_url": "https://gumroad.com/l/vqqqd",
    "tracker_url": "https://blenderartists.org/t/references-matching-setting-transforms-and-opacity-of-backgroud"
                   "-images/1417682",
    "category": "Camera",
}


class CAMERA_OT_ortho_scale(bpy.types.Operator):
    """Adjust orthographic camera scale while focusing on the 3D cursor"""

    bl_idname = "camera.ortho_scale"
    bl_label = "Orthographic Scale"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        ob = context.object
        space = context.space_data
        return ob and ob.type == 'CAMERA' and ob.data.type == 'ORTHO' and space.region_3d.view_perspective == 'CAMERA'

    def __init__(self):
        self.cam: Optional[Object] = None

        self.last_mouse_x: int = 0
        self.init_scale: float = 0
        self.init_matrix: Optional[Matrix] = None

    def invoke(self, context, event):
        self.cam = context.object

        self.last_mouse_x = event.mouse_region_x
        self.init_scale = self.cam.data.ortho_scale
        self.init_matrix = self.cam.matrix_world.copy()

        context.workspace.status_text_set(text="LMB, ENTER: Confirm | RMB, ESC: Cancel")
        context.window.cursor_modal_set('MOVE_X')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        if event.type == 'MOUSEMOVE':
            mouse_x = event.mouse_region_x  # mouse position
            divisor = 3000 if event.shift else 300  # sensitivity divisor
            offset_x = mouse_x - self.last_mouse_x  # offset of cursor

            ortho_scale_offset = offset_x / divisor
            ortho_scale = self.cam.data.ortho_scale - ortho_scale_offset
            ortho_scale = max(ortho_scale, 0.01)

            set_ortho_scale(context, self.cam, ortho_scale)

            context.area.header_text_set("Orthographic Scale: {:.3f}".format(ortho_scale))
            self.last_mouse_x = event.mouse_region_x

        elif event.value == 'PRESS':

            if event.type in ('ESC', 'RIGHTMOUSE'):
                self.restore()
                self.finish(context)
                return {'CANCELLED'}

            elif event.type in ('SPACE', 'LEFTMOUSE'):
                self.finish(context)
                return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def restore(self):
        self.cam.data.ortho_scale = self.init_scale
        self.cam.matrix_world = self.init_matrix

    @staticmethod
    def finish(context):
        context.area.header_text_set(text=None)
        context.workspace.status_text_set(text=None)
        context.window.cursor_modal_restore()


def set_ortho_scale(context, cam, ortho_scale):
    cam_ortho_scale = cam.data.ortho_scale
    new_ortho_scale = ortho_scale

    if round(cam_ortho_scale, 3) != round(new_ortho_scale, 3):
        cam_mat = cam.matrix_world
        cursor_mat = context.scene.cursor.matrix

        cursor_matrix_cam_space = cam_mat.inverted() @ cursor_mat
        loc, rot, scale = cursor_matrix_cam_space.decompose()

        cursor_offset_x = loc[0]  # e.g -2.19 from camera center to cursor
        cursor_offset_y = loc[1]  # e.g 0.70 from camera center to cursor

        # e.g -0.87 from camera center to cursor
        cursor_perc_x = cursor_offset_x / (cam_ortho_scale / 2)
        # new offset that cursor should have to keep the same position after changing ortho scale
        new_cursor_offset_x = cursor_perc_x * (new_ortho_scale / 2)
        # transform of camera needed to give cursor new offset
        cam_transform_x = new_cursor_offset_x - cursor_offset_x

        # e.g 0.28 from camera center to cursor
        cursor_perc_y = cursor_offset_y / (cam_ortho_scale / 2)
        # new offset that should have cursor to keep same position after changing ortho scale
        new_cursor_offset_y = cursor_perc_y * (new_ortho_scale / 2)
        # transform of camera to give cursor new offset
        cam_transform_y = new_cursor_offset_y - cursor_offset_y

        transform_matrix = Matrix.Translation((-cam_transform_x, -cam_transform_y, 0))

        cam.matrix_world = cam.matrix_world @ transform_matrix
        cam.data.ortho_scale = new_ortho_scale


class OrthoScalePreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        col.label(text="How to Use:")
        col.label(text="Activate an orthographic camera with a background, select it, use the addon shortcut "
                       "and move the mouse cursor in horizontal directions.")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Shortcut:")
        self.draw_keymap_items(col, "Object Mode", addon_keymaps, False)

    @staticmethod
    def draw_keymap_items(col, km_name, keymap, allow_remove):
        kc = bpy.context.window_manager.keyconfigs.user
        km = kc.keymaps.get(km_name)
        kmi_idnames = [km_tuple[1].idname for km_tuple in keymap]
        if allow_remove:
            col.context_pointer_set("keymap", km)

        kmis = [kmi for kmi in km.keymap_items if
                kmi.idname in kmi_idnames]
        for kmi in kmis:
            rna_keymap_ui.draw_kmi(['ADDON', 'USER', 'DEFAULT'], kc, km, kmi, col, 0)


classes = (
    CAMERA_OT_ortho_scale,
    OrthoScalePreferences,
)


addon_keymaps = []


def register_keymaps():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')

        kmi = km.keymap_items.new("camera.ortho_scale", 'S', 'PRESS', alt=True)
        addon_keymaps.append((km, kmi))


def unregister_keymaps():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    register_keymaps()


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    unregister_keymaps()


if __name__ == "__main__":
    register()
