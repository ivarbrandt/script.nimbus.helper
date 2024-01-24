import xbmc, xbmcgui, xbmcvfs
import xml.etree.ElementTree as ET
from xml.dom import minidom

KEYMAP_LOCATION = "special://userdata/keymaps/"
POSSIBLE_KEYMAP_NAMES = ["gen.xml", "keyboard.xml", "keymap.xml"]

def set_image():
    image_file = xbmcgui.Dialog().browse(
        2, "Choose Custom Background Image", "network", ".jpg|.png|.bmp", False, False
    )
    if image_file:
        xbmc.executebuiltin("Skin.SetString(CustomBackground,%s)" % image_file)


def fix_black_screen():
    if xbmc.getCondVisibility("Skin.HasSetting(TrailerPlaying)"):
        xbmc.executebuiltin("Skin.ToggleSetting(TrailerPlaying)")
        
def set_blurradius():
    current_value = xbmc.getInfoLabel('Skin.String(BlurRadius)') or "40"
    dialog = xbmcgui.Dialog()
    value = dialog.numeric(0, "Enter blur radius value", current_value)
    if value == "":
        value = "40"
    xbmc.executebuiltin(f"Skin.SetString(BlurRadius,{value})")

def set_blursaturation():
    current_value = xbmc.getInfoLabel('Skin.String(BlurSaturation)') or "2.5"
    keyboard = xbmc.Keyboard(current_value, "Enter blur saturation value")
    keyboard.doModal()
    if keyboard.isConfirmed():
        text = keyboard.getText()
        if text == "":
            text = "2.5"
        xbmc.executebuiltin(f"Skin.SetString(BlurSaturation,{text})")

# def get_current_keymap_path():
#     for keymap_name in POSSIBLE_KEYMAP_NAMES:
#         keymap_path = xbmcvfs.translatePath(KEYMAP_LOCATION + keymap_name)
#         if xbmcvfs.exists(keymap_path):
#             return keymap_path
#     return None

def make_backup(keymap_path):
    backup_path = f"{keymap_path}.backup"
    if not xbmcvfs.exists(backup_path):
        xbmcvfs.copy(keymap_path, backup_path)


def restore_from_backup(keymap_path):
    backup_path = f"{keymap_path}.backup"
    if xbmcvfs.exists(backup_path):
        xbmcvfs.delete(keymap_path)
        xbmcvfs.rename(backup_path, keymap_path)


def get_all_existing_keymap_paths():
    existing_paths = []
    for name in POSSIBLE_KEYMAP_NAMES:
        path = xbmcvfs.translatePath(f"special://profile/keymaps/{name}")
        if xbmcvfs.exists(path):
            existing_paths.append(path)
    return existing_paths


def create_new_keymap_file():
    default_keymap_name = "gen.xml"
    new_keymap_path = xbmcvfs.translatePath(f"{KEYMAP_LOCATION}{default_keymap_name}")
    root = ET.Element("keymap")
    tree = ET.ElementTree(root)
    tree.write(new_keymap_path)
    return new_keymap_path


def modify_keymap():
    keymap_paths = get_all_existing_keymap_paths()
    if not keymap_paths:
        new_keymap_path = create_new_keymap_file()
        keymap_paths = [new_keymap_path]
    setting_value = xbmc.getInfoLabel("Skin.String(trailerSetting)")
    for keymap_path in keymap_paths:
        if setting_value == '1':
            make_backup(keymap_path)
            tree = ET.parse(keymap_path)
            root = tree.getroot()
            play_pause_tags = root.findall(".//play_pause[@mod='longpress']")
            t_key_tags = root.findall(".//t")
            global_tag = root.find("global")
            if global_tag is None:
                global_tag = ET.SubElement(root, "global")
            keyboard_tag = global_tag.find("keyboard")
            if keyboard_tag is None:
                keyboard_tag = ET.SubElement(global_tag, "keyboard")
            for tag_list in [play_pause_tags, t_key_tags]:
                for tag in tag_list:
                    tag.text = "RunScript(script.nimbus.helper, mode=play_trailer)"
            if not t_key_tags:
                ET.SubElement(keyboard_tag, "t").text = "RunScript(script.nimbus.helper, mode=play_trailer)"
            if not play_pause_tags:
                ET.SubElement(keyboard_tag, "play_pause", mod="longpress").text = "RunScript(script.nimbus.helper, mode=play_trailer)"
            pretty_xml = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="  ")
            with xbmcvfs.File(keymap_path, "w") as xml_file:
                xml_file.write("\n".join([line for line in pretty_xml.split("\n") if line.strip()]))
        else:
            restore_from_backup(keymap_path)
    xbmc.executebuiltin("Action(reloadkeymaps)")
