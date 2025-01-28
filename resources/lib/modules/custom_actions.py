import xbmc, xbmcaddon, xbmcgui, xbmcvfs
import xml.etree.ElementTree as ET
from xml.dom import minidom
from threading import Timer
import sys, re
import requests

KEYMAP_LOCATION = "special://userdata/keymaps/"
POSSIBLE_KEYMAP_NAMES = ["gen.xml", "keyboard.xml", "keymap.xml"]


def show_changelog():
    helper_addon = xbmcaddon.Addon("script.nimbus.helper")
    helper_version = helper_addon.getAddonInfo("version")
    skin_addon = xbmcaddon.Addon("skin.nimbus")
    skin_version = skin_addon.getAddonInfo("version")
    skin_name = skin_addon.getAddonInfo("name")
    changelog_path = xbmcvfs.translatePath("special://skin/nimbuschangelog.txt")
    with xbmcvfs.File(changelog_path) as file:
        changelog_text = file.read()
    if isinstance(changelog_text, bytes):
        changelog_text = changelog_text.decode("utf-8")
    changelog_text = re.sub(
        r"\[COLOR \w+\](Version \d+\.\d+\.\d+)\[/COLOR\]",
        r"[COLOR $VAR[MenuSelectorColor]]\1[/COLOR]",
        changelog_text,
    )
    changelog_text = re.sub(
        r"\[COLOR \w+\](Version \$INFO\[.*?\])\[/COLOR\]",
        r"[COLOR $VAR[MenuSelectorColor]]\1[/COLOR]",
        changelog_text,
    )
    helper_pattern = r"Nimbus Helper: Latest: v([\d.]+) \[B\]\|\[/B\] Installed: v.*"
    helper_match = re.search(helper_pattern, changelog_text)
    if helper_match:
        latest_helper_version = helper_match.group(1)
        installed_part = f"Installed: v{helper_version}"
        if helper_version != latest_helper_version:
            installed_part = f"[COLOR red][B]{installed_part}[/B][/COLOR]"
            update_message = (
                "\n\n[COLOR red][B]An update is available for the Nimbus Helper. "
                "Please follow these instructions to update and get the latest features and ensure full continued functionality:[/B][/COLOR]"
                "\n\n1. Go to Settings [B]»[/B] System [B]»[/B] Addons tab [B]»[/B] Manage dependencies"
                "\n2. Find Nimbus Helper and click it"
                "\n3. Versions [B]»[/B] Click the latest version in ivarbrandt's Repository"
            )
        else:
            update_message = "\n\n[COLOR limegreen][B]Nimbus Helper up to date. No updates needed at this time.[/B][/COLOR]"
        new_helper_info = f"Nimbus Helper: Latest: v{latest_helper_version} [B]|[/B] {installed_part}{update_message}"
        changelog_text = re.sub(
            helper_pattern, new_helper_info, changelog_text, count=1
        )
    header = f"CHANGELOG: {skin_name} v{skin_version}"
    dialog = xbmcgui.Dialog()
    dialog.textviewer(header, changelog_text)


def set_widget_count():
    if len(sys.argv) >= 3:
        list_id = sys.argv[2]
        if len(list_id) in (4, 5):
            container_id = (
                f"{list_id[:2]}001" if len(list_id) == 5 else f"{list_id[0]}001"
            )
            num_items_str = xbmc.getInfoLabel(f"Container({container_id}).NumItems")
            if num_items_str and num_items_str.isdigit():
                num_widgets = int(num_items_str) * 2 - 1
                xbmc.executebuiltin(f"Skin.SetString(TotalWidgetCount,{num_widgets})")


def set_image():
    last_path = xbmc.getInfoLabel("Skin.String(LastImagePath)")
    image_file = xbmcgui.Dialog().browse(
        2,
        "Choose Custom Background Image",
        "files" if last_path else "network",
        ".jpg|.png|.bmp",
        False,
        False,
        last_path,
    )
    if image_file:
        xbmc.executebuiltin(f"Skin.SetString(LastImagePath,{image_file})")
        xbmc.executebuiltin(f"Skin.SetString(NimbusCustomBackground,{image_file})")


def play_trailer():
    # if not xbmc.getCondVisibility(
    #     "String.IsEmpty(Window(Home).Property(nimbus.trailer_ready))"
    # ):
    is_episode = xbmc.getCondVisibility("String.IsEqual(ListItem.DBType,episode)")
    is_season = xbmc.getCondVisibility("String.IsEqual(ListItem.DBType,season)")
    if xbmc.getCondVisibility("Control.IsVisible(500) | Control.IsVisible(501)"):
        xbmc.executebuiltin(
            "Notification(Trailer Playback, Trailer playback is not available in this view, 3000)"
        )
    elif not (is_episode or is_season):
        trailer_source = xbmc.getInfoLabel("Skin.String(TrailerSource)")
        play_url = None
        if trailer_source == "0":
            play_url = xbmc.getInfoLabel("ListItem.Trailer")
        elif trailer_source == "1":
            play_url = xbmc.getInfoLabel("Skin.String(TrailerPlaybackURL)")
        if play_url:
            xbmc.executebuiltin("Skin.SetString(TrailerPlaying, true)")
            if xbmc.getCondVisibility("Control.IsVisible(50) | Control.IsVisible(51)"):
                xbmc.executebuiltin(f"PlayMedia({play_url},0,noresume)")
            else:
                xbmc.executebuiltin(f"PlayMedia({play_url},1,noresume)")


def check_api_key(api_key):
    api_url = "https://mdblist.com/api/"
    params = {
        "apikey": api_key,
        "i": "tt0111161",
    }
    try:
        response = requests.get(api_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return ("valid", "ratings" in data and len(data["ratings"]) > 0)
    except requests.RequestException:
        return ("error", None)


def validate_api_key(api_key, silent=True):
    if not api_key:
        xbmc.executebuiltin("Skin.Reset(valid_api_key)")
        return
    xbmc.executebuiltin("Skin.SetString(checking_api_key,true)")
    try:
        status, is_valid = check_api_key(api_key)
        if status == "valid" and is_valid:
            xbmc.executebuiltin("Skin.SetString(valid_api_key,true)")
            if not silent:
                xbmcgui.Dialog().notification(
                    "Success",
                    "Features activated",
                    xbmcgui.NOTIFICATION_INFO,
                    3000,
                )
        elif status == "valid" and not is_valid:
            xbmc.executebuiltin("Skin.Reset(valid_api_key)")
        else:
            if not silent:
                xbmcgui.Dialog().notification(
                    "Connection Error",
                    "Unable to reach MDbList",
                    xbmcgui.NOTIFICATION_INFO,
                    3000,
                )
    finally:
        xbmc.executebuiltin("Skin.Reset(checking_api_key)")


def set_api_key():
    current_key = xbmc.getInfoLabel("Skin.String(mdblist_api_key)")
    keyboard = xbmc.Keyboard(current_key, "Enter MDbList API Key")
    keyboard.doModal()
    if keyboard.isConfirmed():
        new_key = keyboard.getText()
        if not new_key:
            xbmc.executebuiltin("Skin.Reset(mdblist_api_key)")
            xbmc.executebuiltin("Skin.Reset(valid_api_key)")
        else:
            xbmc.executebuiltin(f'Skin.SetString(mdblist_api_key,"{new_key}")')
            validate_api_key(new_key, silent=False)


def check_api_key_on_load():
    api_key = xbmc.getInfoLabel("Skin.String(mdblist_api_key)")
    validate_api_key(api_key, silent=True)


def fix_black_screen():
    if xbmc.getCondVisibility("Skin.HasSetting(TrailerPlaying)"):
        xbmc.executebuiltin("Skin.Reset(TrailerPlaying)")


def set_blurradius():
    current_value = xbmc.getInfoLabel("Skin.String(BlurRadius)") or "30"
    dialog = xbmcgui.Dialog()
    value = dialog.numeric(0, "Enter blur radius value", current_value)
    if value == "":
        value = "30"
    xbmc.executebuiltin(f"Skin.SetString(BlurRadius,{value})")


def set_blursaturation():
    current_value = xbmc.getInfoLabel("Skin.String(BlurSaturation)") or "1.5"
    keyboard = xbmc.Keyboard(current_value, "Enter blur saturation value")
    keyboard.doModal()
    if keyboard.isConfirmed():
        text = keyboard.getText()
        if text == "":
            text = "1.5"
        xbmc.executebuiltin(f"Skin.SetString(BlurSaturation,{text})")


def set_autoendplaybackdelay():
    current_value = xbmc.getInfoLabel("Skin.String(PlaybackDelayMins)") or "30"
    dialog = xbmcgui.Dialog()
    value_mins = dialog.numeric(0, "Enter delay in minutes", current_value)
    if value_mins == "":
        value_mins = "30"
        value_secs = 1800
    else:
        value_secs = int(value_mins) * 60
    xbmc.executebuiltin(f"Skin.SetString(PlaybackDelayMins,{value_mins})")
    xbmc.executebuiltin(f"Skin.SetString(PlaybackDelaySecs,{value_secs})")


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


class KeyListener(xbmcgui.WindowXMLDialog):
    TIMEOUT = 7

    def __new__(cls):
        return super(KeyListener, cls).__new__(
            cls, "DialogNotification.xml", xbmcaddon.Addon().getAddonInfo("path")
        )

    def __init__(self):
        self.key = None

    def onInit(self):
        self.getControl(401).setLabel("Starting key listener...")
        self.getControl(402).setLabel("Be ready to press key")

        # Initial delay
        xbmc.sleep(2000)

        # Adjusted countdown start (5 seconds instead of 7)
        countdown_start = self.TIMEOUT - 2

        # Update the label with the countdown
        self.getControl(401).setLabel("Listening for key press...")
        self.getControl(402).setLabel(f"Timeout in {countdown_start} seconds")

        # Start a countdown
        for i in range(countdown_start, 1, -1):
            self.getControl(402).setLabel(f"Timeout in {i} seconds")
            xbmc.sleep(1000)

        # Handle the last second separately
        self.getControl(402).setLabel("Timeout in 1 second")
        xbmc.sleep(1000)

        # Close the dialog after the countdown finishes
        self.close()

    def onAction(self, action):
        button_code = action.getButtonCode()
        action_id = action.getId()

        # Use button code if it's not 0, otherwise use action ID
        self.key = button_code if button_code != 0 else action_id

        # Update the label to show the captured key
        self.getControl(401).setLabel("Key captured successfully!")
        self.getControl(402).setLabel(f"Captured key code: {self.key}")

        xbmc.sleep(2000)
        self.close()

    @staticmethod
    def record_key():
        dialog = KeyListener()
        timeout = Timer(KeyListener.TIMEOUT, dialog.close)
        timeout.start()
        dialog.doModal()
        timeout.cancel()
        key = dialog.key
        del dialog
        return key


# Function to use the key listener
def capture_user_key():
    listener = KeyListener()
    captured_key = listener.record_key()

    if captured_key:
        # Store the captured key code in a skin string if a key was captured
        xbmc.executebuiltin(f"Skin.SetString(CapturedKeyCode, {captured_key})")

    del listener

    return captured_key


def modify_keymap():
    keymap_paths = get_all_existing_keymap_paths()
    if not keymap_paths:
        new_keymap_path = create_new_keymap_file()
        keymap_paths = [new_keymap_path]

    captured_key = xbmc.getInfoLabel("Skin.String(CapturedKeyCode)")
    if not captured_key:
        return

    setting_value = xbmc.getInfoLabel("Skin.String(trailerSetting)")

    for keymap_path in keymap_paths:
        if setting_value == "1":
            make_backup(keymap_path)
            tree = ET.parse(keymap_path)
            root = tree.getroot()

            # Check if the script action already exists and update it
            found = False
            for key_tag in root.findall(".//key"):
                if key_tag.text == "RunScript(script.nimbus.helper, mode=play_trailer)":
                    key_tag.set("id", captured_key)
                    found = True
                    break

            # If not found, create a new key element
            if not found:
                global_tag = root.find("global")
                if global_tag is None:
                    global_tag = ET.SubElement(root, "global")
                keyboard_tag = global_tag.find("keyboard")
                if keyboard_tag is None:
                    keyboard_tag = ET.SubElement(global_tag, "keyboard")
                ET.SubElement(keyboard_tag, "key", id=captured_key).text = (
                    "RunScript(script.nimbus.helper, mode=play_trailer)"
                )

            pretty_xml = minidom.parseString(ET.tostring(root, "utf-8")).toprettyxml(
                indent="  "
            )
            with xbmcvfs.File(keymap_path, "w") as xml_file:
                xml_file.write(
                    "\n".join([line for line in pretty_xml.split("\n") if line.strip()])
                )

        else:
            restore_from_backup(keymap_path)

    xbmc.executebuiltin("Action(reloadkeymaps)")


# def modify_keymap():
#     keymap_paths = get_all_existing_keymap_paths()
#     if not keymap_paths:
#         new_keymap_path = create_new_keymap_file()
#         keymap_paths = [new_keymap_path]
#     setting_value = xbmc.getInfoLabel("Skin.String(trailerSetting)")
#     for keymap_path in keymap_paths:
#         if setting_value == '1':
#             make_backup(keymap_path)
#             tree = ET.parse(keymap_path)
#             root = tree.getroot()
#             play_pause_tags = root.findall(".//play_pause[@mod='longpress']")
#             t_key_tags = root.findall(".//t")
#             global_tag = root.find("global")
#             if global_tag is None:
#                 global_tag = ET.SubElement(root, "global")
#             keyboard_tag = global_tag.find("keyboard")
#             if keyboard_tag is None:
#                 keyboard_tag = ET.SubElement(global_tag, "keyboard")
#             for tag_list in [play_pause_tags, t_key_tags]:
#                 for tag in tag_list:
#                     tag.text = "RunScript(script.nimbus.helper, mode=play_trailer)"
#             if not t_key_tags:
#                 ET.SubElement(keyboard_tag, "t").text = "RunScript(script.nimbus.helper, mode=play_trailer)"
#             if not play_pause_tags:
#                 ET.SubElement(keyboard_tag, "play_pause", mod="longpress").text = "RunScript(script.nimbus.helper, mode=play_trailer)"
#             pretty_xml = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="  ")
#             with xbmcvfs.File(keymap_path, "w") as xml_file:
#                 xml_file.write("\n".join([line for line in pretty_xml.split("\n") if line.strip()]))
#         else:
#             restore_from_backup(keymap_path)
#     xbmc.executebuiltin("Action(reloadkeymaps)")
