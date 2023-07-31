#----------------------------------------------------------
# File __init__.py
#----------------------------------------------------------
# flow
# clear all images > create images > get all images in folder > greate/get meta files > create symbols > create keyframes >
# create layer > create animation > clear unused meta
import bpy
from bpy.types import Operator

from . import exportPanel

bl_info = {
    "name": "Fraytools Animation Exporter",
    "author": "Chubs",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D",
    "description": "Export NLA strips to a a fraytools project",
    "warning": "",
    "doc_url": "",
    "category": "Animation",
}

classes = (
    exportPanel.FE_PT_PANEL,
    exportPanel.exportNLAButton,
    exportPanel.SelectExportFolder,
    exportPanel.SelectEntity,
    exportPanel.SpriteProperties,
    exportPanel.FolderProperties,
    exportPanel.CenterSpritePos,
    exportPanel.CenterSpritePiv
)

register, unregister = bpy.utils.register_classes_factory(classes)
