#----------------------------------------------------------
# File exportPanel.py
#----------------------------------------------------------
import bpy
import os
import uuid
import json
from pathlib import Path
from bpy_extras.io_utils import ImportHelper
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator
import math

from . import entityFuncs

# function I totally didn't yoink from PsnDth
#  opens file and returns json contents
def json_contents(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)

# find an existing key from name
def FindKeyFromName(jsonData, name, type):
    for index, anim in enumerate(jsonData[type]):
        if anim["name"] == name:
            return jsonData[type][index]
    return None

# find an existing key from name
def FindKeyFromGUID(jsonData, GUID, type):
    for index, layer in enumerate(jsonData[type]):
        if layer["$id"] == GUID:
            return jsonData[type][index]
    return None

# find an existing key from both GUID and name
def FindKeyFromGUIDAndName(jsonData, GUID, name, type):
    print ("GUID AND NAME: " + GUID + " " + name)
    for index, anim in enumerate(jsonData[type]):
        if anim["name"] == name and anim["$id"] == GUID:
            return jsonData[type][index]
        else:
            print ()
    return None

# clear a key using GUID
def clearKeyFromGUID(jsonData, GUID, type):
    for index, key in enumerate(jsonData[type]):
        if key["$id"] == GUID:
            jsonData[type].pop(index)
            return
    return

# Clears Keyframes and Symbols of the desired animation
def ClearKeyframesAndSymbols(entity, AnimationName, LayerName):
    Animation = FindKeyFromName(entity, AnimationName, "animations")
    if Animation:
        for layerID in Animation["layers"]:
            Layer = FindKeyFromGUIDAndName(entity, layerID, LayerName, "layers")
            if Layer:
                for keyframe in Layer["keyframes"]:
                    key = FindKeyFromGUID(entity, keyframe, "keyframes")
                    if key:
                        clearKeyFromGUID(entity, key["symbol"], "symbols")
                        clearKeyFromGUID(entity, keyframe, "keyframes")

# Main export function
def ExportNLA(self, context):
    # check if path is valid
    if not os.path.isdir(context.scene.folderProp.export):
        return

    output_dir = context.scene.folderProp.export
    scene = bpy.context.scene

    # make a list of strips used in the NLA
    # strips are found in -
    # object.animation_data.nla_tracks[TrackName].strips[stripName]
    nla_strips = []
    object = None
    for obj in scene.objects:
        if obj.animation_data and obj.animation_data.nla_tracks:
            object = obj
            for track in obj.animation_data.nla_tracks:
                if not track.mute:
                    for strip in track.strips:
                        nla_strips.append((strip, strip.mute, track))
                        strip.mute = True

    if not nla_strips:
        print("no animations to export")
        return

    # save to restore later
    orig_frame_start = scene.frame_start
    orig_frame_end = scene.frame_end
    orig_frame_step = scene.frame_step
    orig_filepath = scene.render.filepath
    # render each strip

    entityData = json_contents(context.scene.folderProp.entity)

    for strip in nla_strips:
        scene.render.filepath = output_dir + strip[2].name + '\\'
        scene.frame_start = int(strip[0].frame_start)
        scene.frame_end = int(strip[0].frame_end)
        scene.frame_step = int(context.scene.spriteProp.step)

        # reset bones before rendering
        # this ensures keyframes from other tracks don't
        # get mixed in with the current animation
        for n in object.pose.bones:
            print("resetting bone: " + n.name)
            n.location = (0, 0, 0)
            n.rotation_quaternion = (1, 0, 0, 0)
            n.rotation_axis_angle = (0, 0, 1, 0)
            n.rotation_euler = (0, 0, 0)
            n.scale = (1, 1, 1)

        print(scene.render.filepath)
        # clear out all png files to ready for re-exporting
        if os.path.isdir(scene.render.filepath):
            print("path exists")
            for images in os.listdir(scene.render.filepath):
                print("images")
                if (images.endswith(".png")):
                    print("remove")
                    os.remove(os.path.join(scene.render.filepath, images))

        strip[0].mute = False
        bpy.ops.render.render(animation=True)
        folder_dir = scene.render.filepath
        folder_name = os.path.basename(scene.render.filepath)

        # Clear animations previous keyframes and Symbols
        # this ensures that there is no leftover unused keyframes and symbols bloating the filesize
        ClearKeyframesAndSymbols(entityData, strip[2].name, context.scene.spriteProp.layerName)

        symbols = []
        keyframes = []
        animID = ""
        for images in os.listdir(folder_dir):
            if (images.endswith(".png")):
                img = scene.render.filepath + images

                #Create Meta, Keyframe & Symbol for Image
                keyframes.append(entityFuncs.createImage(
                    entityData,
                    img,
                    context.scene.spriteProp.length,
                    context.scene.spriteProp.spriteX,
                    context.scene.spriteProp.spriteY,
                    context.scene.spriteProp.pivotX,
                    context.scene.spriteProp.pivotY,
                    1,
                    1,
                    0
                ))

        # Clear unused meta files
        for meta in os.listdir(folder_dir):
            if (meta.endswith(".meta")):
                if not os.path.isfile(scene.render.filepath + os.path.splitext(meta)[0]):
                    os.remove(os.path.join(scene.render.filepath, meta))

        # Check if Animation exists if not, create it
        Anim = FindKeyFromName(entityData, strip[2].name, "animations")
        if not Anim:
            layer = entityFuncs.createLayer(keyframes, context.scene.spriteProp.layerName)
            layID = layer["$id"]
            animation = entityFuncs.createAnimation(strip[2].name, layID)

            entityData["layers"].append(layer)
            entityData["animations"].append(animation)
            animID = animation["$id"]
        else:

            # Check if Layer exists if not, create it
            Lay = FindKeyFromName(entityData, context.scene.spriteProp.layerName, "layers")
            if not Lay:
                layer = entityFuncs.createLayer(keyframes, context.scene.spriteProp.layerName)
                layID = layer["$id"]
                Anim["layers"].append(layID)

                entityData["layers"].append(layer)
            else:
                Lay["keyframes"] = keyframes

        strip[0].mute = True

    # save changes to entity file
    with open(context.scene.folderProp.entity, "w") as entData:
        json.dump(entityData, entData, indent=4)

    # restore changes we made
    scene.frame_start = orig_frame_start
    scene.frame_end = orig_frame_end
    scene.frame_step = orig_frame_step
    scene.render.filepath = orig_filepath

    for strip in nla_strips:
        strip[0].mute = strip[1]
## EXPORT NLA END ##

# Props for selecting files and folders
class FolderProperties(bpy.types.PropertyGroup):
    @classmethod
    def register(cls):
        bpy.types.Scene.folderProp = bpy.props.PointerProperty(type=FolderProperties)

    @classmethod
    def unregister(cld):
        del bpy.types.Scene.folderProp

    entity: bpy.props.StringProperty(
        name = "Entity",
        description=":",
        default=""
        )

    export: bpy.props.StringProperty(
        name = "Export Dir",
        description=":",
        default=""
        )

# Props pertaining to exported sprite information
class SpriteProperties(bpy.types.PropertyGroup):
    @classmethod
    def register(cls):
        bpy.types.Scene.spriteProp = bpy.props.PointerProperty(type=SpriteProperties)

    @classmethod
    def unregister(cld):
        del bpy.types.Scene.spriteProp

    spriteX: bpy.props.FloatProperty(
        name = "spriteX",
        description="",
        default=0.0,
        )

    spriteY: bpy.props.FloatProperty(
        name = "spriteY",
        description="",
        default=0.0,
        )

    pivotX: bpy.props.FloatProperty(
        name = "pivotX",
        description="",
        default=0.0,
        )

    pivotY: bpy.props.FloatProperty(
        name = "pivotY",
        description="",
        default=0.0,
        )

    layerName: bpy.props.StringProperty(
        name = "Layer",
        description=":",
        default="GeneratedAnim"
        )

    length: bpy.props.IntProperty(
        name = "Keyframe Length",
        description="",
        min = 1,
        default=1,
        )

    step: bpy.props.IntProperty(
        name = "Keyframe step",
        description="",
        min = 1,
        default=1,
        )

# Center sprite position based on render resolution
class CenterSpritePos(bpy.types.Operator):
    """Export NLA strips to the selected Fraytools project"""
    bl_idname = "sprite.center_pos"
    bl_label = "Center Sprite Position"

    def execute(self, context):
        context.scene.spriteProp.spriteX = -bpy.context.scene.render.resolution_x/2
        context.scene.spriteProp.spriteY = -bpy.context.scene.render.resolution_y/2
        return {'FINISHED'}

# Center sprite pivot based on render resolution
class CenterSpritePiv(bpy.types.Operator):
    """Export NLA strips to the selected Fraytools project"""
    bl_idname = "sprite.center_piv"
    bl_label = "Center Sprite Pivot"

    def execute(self, context):
        context.scene.spriteProp.pivotX = -bpy.context.scene.render.resolution_x/2
        context.scene.spriteProp.pivotY = -bpy.context.scene.render.resolution_y/2
        return {'FINISHED'}

# Select Entity button
class SelectEntity(bpy.types.Operator, ImportHelper):
    """Entity to Export too"""
    bl_idname= "export.entity"
    bl_label = "Select Entity"

    filename_ext = ".entity"

    filter_glob: bpy.props.StringProperty(
        default="*.entity",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def invoke(self, context, event):
        filename, extension = os.path.splitext(bpy.data.filepath)
        self.filepath = filename + ".entity"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        userpath = self.properties.filepath
        filename, extension = os.path.splitext(self.filepath)
        if not extension == ".entity":
            msg = "Please select an entity file\n" + userpath
            self.report({'WARNING'}, msg)
        else:
            context.scene.folderProp.entity = self.filepath
        return {"FINISHED"}

# Select sprite export folder button
class SelectExportFolder(bpy.types.Operator, ExportHelper):
    """Folder to Export to"""
    bl_idname= "export.folder"
    bl_label = "Select Export Folder"
    #bl_options = {"REGISTER"}

    filename_ext = ""

    use_filter = True
    use_filter_folder = True

    set_default_filter_settings: bool = True
    def draw(self, context):
        if self.set_default_filter_settings:
            context.space_data.params.use_filter = True
            context.space_data.params.use_filter_folder = True
            self.set_default_filter_settings = False

    directory = bpy.props.StringProperty(
        name="Export Path",
        description="Export Directory"
    )

    def invoke(self, context, event):
        self.filepath = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        userpath = self.properties.filepath
        if not os.path.isdir(userpath):
            msg = "Please select a directory not a file\n" + userpath
            self.report({'WARNING'}, msg)
        else:
            context.scene.folderProp.export = self.filepath
        return {"FINISHED"}

# export NLA button
class exportNLAButton(bpy.types.Operator):
    """Export NLA strips to the selected Fraytools project"""
    bl_idname = "object.export_nla"
    bl_label = "Export NLA strips"

    def execute(self, context):
        ExportNLA(self, context)
        return {'FINISHED'}

# main Panel
class FE_PT_PANEL(bpy.types.Panel):
    bl_label = "Fraytools Exporter"
    bl_idname = "FE_RENDER_PT_LAYOUT"
    bl_category = "Fraytools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.scale_y = 1.1
        row.prop(context.scene.folderProp, "entity")
        row.operator("export.entity", text="", icon="FILE_FOLDER")

        row = layout.row()
        row.scale_y = 1.1
        row.prop(context.scene.folderProp, "export")
        row.operator("export.folder", text="", icon="FILE_FOLDER")

        row = layout.row()
        row.scale_y = 1
        row.prop(context.scene.spriteProp, "spriteX")
        row.prop(context.scene.spriteProp, "pivotX")

        row = layout.row()
        row.scale_y = 1
        row.prop(context.scene.spriteProp, "spriteY")
        row.prop(context.scene.spriteProp, "pivotY")

        row = layout.row()
        row.scale_y = 1
        row.operator("sprite.center_pos")
        row.operator("sprite.center_piv")

        row = layout.row()
        row.scale_y = 1
        row.prop(context.scene.spriteProp, "layerName")

        row = layout.row()
        row.scale_y = 1
        row.prop(context.scene.spriteProp, "length")
        row.prop(context.scene.spriteProp, "step")

        row = layout.row()
        row.scale_y = 0.5

        row = layout.row()
        row.scale_y = 1.3
        row.operator("object.export_nla")
