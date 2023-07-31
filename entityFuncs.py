#----------------------------------------------------------
# File entityFuncs.py
#----------------------------------------------------------
import os
import json
import uuid

def json_contents(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)

def createNewEntity(name):
    guid = str(uuid.uuid4())
    ent = {
        "animations": [],
        "export": True,
        "guid": guid,
        "id": "",
        "keyframes": [],
        "layers": [],
        "paletteMap": {
            "paletteCollection": null,
            "paletteMap": null
        },
        "pluginMetadata": {},
        "plugins": [],
        "symbols": [],
        "tags": [],
        "terrains": [],
        "tilesets": [],
        "version": 14
    }
    return ent

def createSymbol(imageAsset, posX, posY, pivX, pivY, scaleX, scaleY, rot):
    guid = str(uuid.uuid4())
    symb = {
        "$id": guid,
        "alpha": 1,
        "imageAsset": imageAsset,
        "pivotX": pivX,
        "pivotY": pivY,
        "pluginMetadata": {},
        "rotation": rot,
        "scaleX": scaleX,
        "scaleY": scaleY,
        "type": "IMAGE",
        "x": posX,
        "y": posY
    }
    return symb

def createKeyframe(symbol, length):
    guid = str(uuid.uuid4())
    key = {
        "$id": guid,
        "length": 1,
        "pluginMetadata": {},
        "symbol": symbol,
        "tweenType": "LINEAR",
        "tweened": False,
        "type": "IMAGE"
    }
    return key

def createLayer(keyframes, name):
    guid = str(uuid.uuid4())
    lay = {
        "$id": guid,
        "hidden": False,
        "keyframes": keyframes,
        "locked": False,
        "name": name,
        "pluginMetadata": {},
        "type": "IMAGE"
    }
    return lay

def createAnimation(name, layers):
    guid = str(uuid.uuid4())
    anim = {
        "$id": guid,
        "layers": [layers],
        "name": name,
        "pluginMetadata": {}
    }
    return anim

def createPNGMeta(meta):
    guid = str(uuid.uuid4())
    m = {
        "export": False,
        "guid": guid,
        "id": "",
        "pluginMetadata": {},
        "plugins": [],
        "tags": [],
        "version": 2
    }
    with open(meta, "w") as f:
        #j = json.dump(m)
        json.dump(m,f,indent=4)
    return m

def createImage(entity, image, length, posX, posY, pivX, pivY, scaleX, scaleY, rot):
    imageAsset = ""
    meta = None
    if not os.path.isfile(image + ".meta"):
        meta = createPNGMeta(image + ".meta")
    else:
        meta = json_contents(image + ".meta")

    imageAsset = meta["guid"]
    symbol = createSymbol(imageAsset, posX, posY, pivX, pivY, scaleX, scaleY, rot)
    entity["symbols"].append(symbol)
    keyframe = createKeyframe(symbol["$id"], length)
    entity["keyframes"].append(keyframe)
    return keyframe["$id"]
