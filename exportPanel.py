#----------------------------------------------------------
# File exportPanel.py
#----------------------------------------------------------
import bpy
import os
import uuid
import json
from pathlib import Path
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator
import math

def truncate_float(float_number, decimal_places):
    multiplier = 10 ** decimal_places
    return int(float_number * multiplier) / multiplier

def json_contents(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)

def checkIfKeyExists(jsonData, name, type):
    for index, anim in enumerate(jsonData[type]):
        if anim["name"] == name:
            return True, index
    return False, -1

def getLayerFromGUID(jsonData, GUID):
    for index, layer in enumerate(jsonData["layers"]):
        if layer["$id"] == GUID:
            return True, jsonData["layers"][index]
    return False, -1



def clearKeyFromGUID(jsonData, GUID, type):
    for index, key in enumerate(jsonData[type]):
        if key["$id"] == GUID:
            jsonData[type].pop(index)
            return
    return


def ExportNLA(self, context):
    if not os.path.isdir(context.scene.folderProp.export):
        return

    # TODO make this directory selectable
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
    orig_filepath = scene.render.filepath
    masterAnims = []
    # render each strip

    entityData = json_contents(context.scene.folderProp.entity)

    if not os.path.isfile(context.scene.folderProp.export + "exportMaster.meta"):
        with open(context.scene.folderProp.export + "exportMaster.meta", "w") as masterData:
            masterJson = {
                "animations": masterAnims
            }
            json.dump(masterJson, masterData, indent=4)
    else:
        try:
            myjson = json_contents(context.scene.folderProp.export + "exportMaster.meta")
            if not "animations" in myjson:
                with open(context.scene.folderProp.export + "exportMaster.meta", "w") as masterData:
                    masterJson = {
                        "animations": masterAnims
                    }
                    json.dump(masterJson, masterData, indent=4)
        except ValueError as e:
            with open(context.scene.folderProp.export + "exportMaster.meta", "w") as masterData:
                masterJson = {
                    "animations": masterAnims
                }
                json.dump(masterJson, masterData, indent=4)

    master = json_contents(context.scene.folderProp.export + "exportMaster.meta")

    for strip in nla_strips:
        scene.render.filepath = output_dir + strip[2].name + '/'
        scene.frame_start = int(strip[0].frame_start)
        scene.frame_end = int(strip[0].frame_end)

        for n in object.pose.bones:
            print("resetting bone: " + n.name)
            n.location = (0, 0, 0)
            n.rotation_quaternion = (1, 0, 0, 0)
            n.rotation_axis_angle = (0, 0, 1, 0)
            n.rotation_euler = (0, 0, 0)
            n.scale = (1, 1, 1)

        strip[0].mute = False
        bpy.ops.render.render(animation=True)
        folder_dir = scene.render.filepath
        folder_name = os.path.basename(scene.render.filepath)

        curAnimJsonCheck = checkIfKeyExists(master, strip[2].name, "animations")
        if master["animations"] and curAnimJsonCheck[0] == True:
            print("found master for: " + strip[2].name)
            curAnim = master["animations"][curAnimJsonCheck[1]]

            for keyframe in curAnim["keyframes"]:
                print("Clearing: " + keyframe)
                clearKeyFromGUID(entityData, keyframe, "keyframes")

            for symbol in curAnim["symbols"]:
                print("Clearing: " + keyframe)
                clearKeyFromGUID(entityData, symbol, "symbols")

            master["animations"].pop(curAnimJsonCheck[1])

        symbols = []
        keyframes = []
        animID = ""
        for images in os.listdir(folder_dir):
            if (images.endswith(".png")):
                print("Found png: " + scene.render.filepath + images)
                imageGUID = str(uuid.uuid4())
                with open(scene.render.filepath + images + ".meta", "w") as f:
                    p = Path(__file__).with_name("imageJsonTemplate.json")
                    data = json_contents(p)
                    data["guid"] = imageGUID
                    json.dump(data, f, indent=4)

                symbolGUID = str(uuid.uuid4())
                symbols.append(symbolGUID)
                entityData["symbols"].append({
                    "$id": symbolGUID,
                    "alpha": 1,
                    "imageAsset": imageGUID,
                    "pivotX": context.scene.spriteProp.pivotX,
                    "pivotY": context.scene.spriteProp.pivotY,
                    "pluginMetadata": {},
                    "rotation": 0,
                    "scaleX": 1,
                    "scaleY": 1,
                    "type": "IMAGE",
                    "x": context.scene.spriteProp.spriteX,
                    "y": context.scene.spriteProp.spriteY
                })

                keyframeGUID = str(uuid.uuid4())
                keyframes.append(keyframeGUID)
                entityData["keyframes"].append({
                    "$id": keyframeGUID,
                    "length": 1,
                    "pluginMetadata": {},
                    "symbol": symbolGUID,
                    "tweenType": "LINEAR",
                    "tweened": False,
                    "type": "IMAGE"
                })

        animExist = checkIfKeyExists(entityData, strip[2].name, "animations")
        if not animExist[0]:
            print("animation doesn't exist creating new ")
            animID = str(uuid.uuid4())
            spriteLayerGUID = str(uuid.uuid4())
            entityData["layers"].append({
                "$id": spriteLayerGUID,
                "hidden": False,
                "keyframes": keyframes,
                "locked": True,
                "name": "GeneratedAnim",
                "pluginMetadata": {},
                "type": "IMAGE"
            })

            entityData["animations"].append({
                "$id": animID,
                "layers": [spriteLayerGUID],
                "name": strip[2].name,
                "pluginMetadata": {}
            })
        else:
            animation = entityData["animations"][animExist[1]]
            animID = str(uuid.uuid4())
            print(animation["name"])
            layerExist = False
            for layer in animation["layers"]:
                l = getLayerFromGUID(entityData, layer)
                if l[1]["name"] == "GeneratedAnim":
                    l[1]["keyframes"] = keyframes
                    layerExist = True

            if not layerExist:
                spriteLayerGUID = str(uuid.uuid4())
                entityData["layers"].append({
                    "$id": spriteLayerGUID,
                    "hidden": False,
                    "keyframes": keyframes,
                    "locked": True,
                    "name": "GeneratedAnim",
                    "pluginMetadata": {},
                    "type": "IMAGE"
                })
                animation["layers"].append(spriteLayerGUID)

        master["animations"].append({
            "name": strip[2].name,
            "keyframes": keyframes,
            "symbols": symbols
        })
        strip[0].mute = True

    with open(context.scene.folderProp.entity, "w") as entData:
        json.dump(entityData, entData, indent=4)

    with open(context.scene.folderProp.export + "exportMaster.meta", "w") as masterData:
        json.dump(master, masterData, indent=4)


    # restore changes we made
    scene.frame_start = orig_frame_start
    scene.frame_end = orig_frame_end
    scene.render.filepath = orig_filepath

    for strip in nla_strips:
        strip[0].mute = strip[1]
## EXPORT NLA END ##

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
        name = "Layer Name",
        description=":",
        default="GeneratedAnim"
        )

class CenterSpritePos(bpy.types.Operator):
    """Export NLA strips to the selected Fraytools project"""
    bl_idname = "sprite.center_pos"
    bl_label = "Center Sprite Position"

    def execute(self, context):
        context.scene.spriteProp.spriteX = -bpy.context.scene.render.resolution_x/2
        context.scene.spriteProp.spriteY = -bpy.context.scene.render.resolution_y/2
        return {'FINISHED'}

class CenterSpritePiv(bpy.types.Operator):
    """Export NLA strips to the selected Fraytools project"""
    bl_idname = "sprite.center_piv"
    bl_label = "Center Sprite Pivot"

    def execute(self, context):
        context.scene.spriteProp.pivotX = -bpy.context.scene.render.resolution_x/2
        context.scene.spriteProp.pivotY = -bpy.context.scene.render.resolution_y/2
        return {'FINISHED'}

class SelectEntity(bpy.types.Operator, ImportHelper):
    """Entity to Export too"""
    bl_idname= "export.entity"
    bl_label = "Select Entity"
    bl_options = {"REGISTER"}

    directory = bpy.props.StringProperty(
        name="Entity Path",
        description="Export Entity"
    )

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        context.scene.folderProp.entity = self.filepath
        return {"FINISHED"}

class SelectExportFolder(bpy.types.Operator, ImportHelper):
    """Folder to Export too"""
    bl_idname= "export.folder"
    bl_label = "Select Export Folder"
    bl_options = {"REGISTER"}

    directory = bpy.props.StringProperty(
        name="Export Path",
        description="Export Directory"
    )

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        context.scene.folderProp.export = self.filepath
        return {"FINISHED"}

class exportNLAButton(bpy.types.Operator):
    """Export NLA strips to the selected Fraytools project"""
    bl_idname = "object.export_nla"
    bl_label = "Export NLA strips"

    def execute(self, context):
        ExportNLA(self, context)
        return {'FINISHED'}

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
        row.scale_y = 0.5

        row = layout.row()
        row.scale_y = 1.3
        row.operator("object.export_nla")
