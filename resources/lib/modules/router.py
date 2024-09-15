# -*- coding: utf-8 -*-
import sys
from urllib.parse import parse_qsl

# from modules.logger import logger


def routing():
    params = dict(parse_qsl(sys.argv[1], keep_blank_values=True))
    _get = params.get
    mode = _get("mode", "check_for_update")

    if "actions" in mode:
        from modules import actions

        return exec("actions.%s(params)" % mode.split(".")[1])

    if mode == "check_for_update":
        from modules.version_monitor import check_for_update

        return check_for_update(_get("skin_id"))

    if mode == "check_for_profile_change":
        from modules.version_monitor import check_for_profile_change

        return check_for_profile_change(_get("skin_id"))

    if mode == "manage_widgets":
        from modules.cpath_maker import CPaths

        return CPaths(_get("cpath_setting")).manage_widgets()

    if mode == "manage_main_menu_path":
        from modules.cpath_maker import CPaths

        return CPaths(_get("cpath_setting")).manage_main_menu_path()

    if mode == "remake_all_cpaths":
        from modules.cpath_maker import remake_all_cpaths

        return remake_all_cpaths()

    if mode == "search_input":
        from modules.search_utils import SPaths

        return SPaths().search_input()

    if mode == "remove_all_spaths":
        from modules.search_utils import SPaths

        return SPaths().remove_all_spaths()

    if mode == "re_search":
        from modules.search_utils import SPaths

        return SPaths().re_search()

    if mode == "open_search_window":
        from modules.search_utils import SPaths

        return SPaths().open_search_window()

    if mode == "set_api_key":
        from modules.MDbList import set_api_key

        return set_api_key()

    if mode == "delete_all_ratings":
        from modules.MDbList import MDbListAPI

        return MDbListAPI().delete_all_ratings()

    if mode == "set_image":
        from modules.custom_actions import set_image

        return set_image()

    if mode == "capture_user_key":
        from modules.custom_actions import capture_user_key

        return capture_user_key()

    if mode == "modify_keymap":
        from modules.custom_actions import modify_keymap

        return modify_keymap()

    if mode == "play_trailer":
        from modules.MDbList import play_trailer

        return play_trailer()

    if mode == "fix_black_screen":
        from modules.custom_actions import fix_black_screen

        return fix_black_screen()

    if mode == "set_blurradius":
        from modules.custom_actions import set_blurradius

        return set_blurradius()

    if mode == "set_blursaturation":
        from modules.custom_actions import set_blursaturation

        return set_blursaturation()

    if mode == "set_autoendplaybackdelay":
        from modules.custom_actions import set_autoendplaybackdelay

        return set_autoendplaybackdelay()

    if mode == "check_ratings":
        from modules.custom_actions import check_ratings

        return check_ratings()

    if mode == "clear_image_cache":
        from modules.helper import clear_image_cache

        return clear_image_cache()

    if mode == "calculate_cache_size":
        from modules.helper import calculate_cache_size

        return calculate_cache_size()

    if mode == "set_widget_count":
        from modules.custom_actions import set_widget_count

        return set_widget_count()

    if mode == "show_changelog":
        from modules.custom_actions import show_changelog

        return show_changelog()

    if mode == "check_api_key_on_load":
        from modules.MDbList import check_api_key_on_load

        return check_api_key_on_load()
