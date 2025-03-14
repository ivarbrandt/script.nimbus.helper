# -*- coding: utf-8 -*-

import xbmc, xbmcgui, xbmcvfs
import sqlite3 as database
from modules import xmls
from urllib.parse import quote
from threading import Thread, Event

# from modules.logger import logger

SETTINGS_PATH = xbmcvfs.translatePath(
    "special://profile/addon_data/script.nimbus.helper/"
)

SEARCH_DATABASE_PATH = xbmcvfs.translatePath(
    "special://profile/addon_data/script.nimbus.helper/spath_cache.db"
)

search_history_xml = "script-nimbus-search_history"

default_xmls = {
    "search_history": (search_history_xml, xmls.default_history, "SearchHistory")
}

default_path = "addons://sources/video"



class SPaths:
    def __init__(self, spaths=None):
        self.connect_database()
        if spaths is None:
            self.spaths = []
        else:
            self.spaths = spaths
        self.refresh_spaths = False
        self.home_window = xbmcgui.Window(10000)
        self.max_history_items = 100

    def connect_database(self):
        if not xbmcvfs.exists(SETTINGS_PATH):
            xbmcvfs.mkdir(SETTINGS_PATH)
        self.dbcon = database.connect(SEARCH_DATABASE_PATH, timeout=20)
        self.dbcon.execute(
            "CREATE TABLE IF NOT EXISTS spath (spath_id INTEGER PRIMARY KEY AUTOINCREMENT, spath text)"
        )
        self.dbcur = self.dbcon.cursor()

    def add_spath_to_database(self, spath):
        self.refresh_spaths = True
        self.dbcur.execute(
            "INSERT INTO spath (spath) VALUES (?)",
            (spath,),
        )
        self.dbcon.commit()

    def remove_spath_from_database(self, spath_id):
        self.refresh_spaths = True
        self.dbcur.execute("DELETE FROM spath WHERE spath_id = ?", (spath_id,))
        self.dbcon.commit()

    def is_database_empty(self):
        self.dbcur.execute("SELECT COUNT(*) FROM spath")
        rows = self.dbcur.fetchone()[0]
        return rows == 0

    def remove_all_spaths(self, skip_dialog=False):
        count_str = self.home_window.getProperty("nimbus.search.history.count")
        count = int(count_str) if count_str else 0
        if count == 0:
            return
        if not skip_dialog:
            dialog = xbmcgui.Dialog()
            title = "Nimbus"
            prompt = f"You are about to delete [COLOR red][B]{count}[/B][/COLOR] items from your search history.[CR][CR]This action cannot be undone. Proceed?"
            if not dialog.yesno(title, prompt):
                return False
        self.refresh_spaths = True
        self.dbcur.execute("DELETE FROM spath")
        self.dbcur.execute("DELETE FROM sqlite_sequence WHERE name='spath'")
        self.dbcon.commit()
        for i in range(1, 101):
            self.home_window.clearProperty(f"nimbus.search.history.{i}")
            self.home_window.clearProperty(f"nimbus.search.history.{i}.id")
        self.home_window.setProperty("nimbus.search.history.count", "0")
        self.home_window.clearProperty("nimbus.search.input")
        self.home_window.clearProperty("nimbus.search.input.encoded")
        self.home_window.clearProperty("nimbus.search.input.trakt.encoded")
        self.home_window.setProperty("nimbus.search.history.empty", 
                            "Your search history is empty. Click the search icon above to perform a new search.")
        return True

    def fetch_all_spaths(self):
        results = self.dbcur.execute(
            "SELECT * FROM spath ORDER BY spath_id DESC"
        ).fetchall()
        return results

    def check_spath_exists(self, spath):
        result = self.dbcur.execute(
            "SELECT spath_id FROM spath WHERE spath = ?", (spath,)
        ).fetchone()
        return result[0] if result else None
    
    def refresh_search_history(self):
        """Method to refresh search history properties after skin updates"""
        history = self.fetch_all_spaths()
        for i in range(1, self.max_history_items + 1):
            self.home_window.clearProperty(f"nimbus.search.history.{i}")
            self.home_window.clearProperty(f"nimbus.search.history.{i}.id")
        for i, (id, term) in enumerate(history[: self.max_history_items], 1):
            self.home_window.setProperty(f"nimbus.search.history.{i}", term)
            self.home_window.setProperty(f"nimbus.search.history.{i}.id", str(id))
        count = min(len(history), self.max_history_items)
        self.home_window.setProperty("nimbus.search.history.count", str(count))
        if count == 0:
            self.home_window.setProperty(
                "nimbus.search.history.empty",
                "Your search history is empty. Click the search icon to perform a new search.",
            )
        else:
            self.home_window.clearProperty("nimbus.search.history.empty")
    
    def update_search_history_properties(self, search_term, existing_spath_id):
        """Update search history properties to reflect a new search term. Moves existing terms down and places the new/existing term at the top."""
        count_str = self.home_window.getProperty("nimbus.search.history.count")
        count = int(count_str) if count_str else 0
        existing_property_index = None
        for i in range(1, count + 1):
            if self.home_window.getProperty(f"nimbus.search.history.{i}") == search_term:
                existing_property_index = i
                break
        if existing_property_index is not None:
            term_to_move = self.home_window.getProperty(f"nimbus.search.history.{existing_property_index}")
            id_to_move = self.home_window.getProperty(f"nimbus.search.history.{existing_property_index}.id")
            for i in range(existing_property_index, 1, -1):
                prev_term = self.home_window.getProperty(f"nimbus.search.history.{i-1}")
                prev_id = self.home_window.getProperty(f"nimbus.search.history.{i-1}.id")
                self.home_window.setProperty(f"nimbus.search.history.{i}", prev_term)
                self.home_window.setProperty(f"nimbus.search.history.{i}.id", prev_id)
            self.home_window.setProperty("nimbus.search.history.1", term_to_move)
            self.home_window.setProperty("nimbus.search.history.1.id", id_to_move)
        else:
            for i in range(min(count, self.max_history_items - 1), 0, -1):
                term = self.home_window.getProperty(f"nimbus.search.history.{i}")
                term_id = self.home_window.getProperty(f"nimbus.search.history.{i}.id")
                self.home_window.setProperty(f"nimbus.search.history.{i+1}", term)
                self.home_window.setProperty(f"nimbus.search.history.{i+1}.id", term_id)
            self.home_window.setProperty("nimbus.search.history.1", search_term)
            self.home_window.setProperty("nimbus.search.history.1.id", str(existing_spath_id))
            if count < self.max_history_items:
                self.home_window.setProperty("nimbus.search.history.count", str(count + 1))

    def open_search_window(self):
        """Open search window and focus appropriate control based on history state"""
        if xbmcgui.getCurrentWindowId() == 10000:
            xbmc.executebuiltin("ActivateWindow(1121)")
        self.home_window.clearProperty("nimbus.search.input")
        self.home_window.clearProperty("nimbus.search.input.encoded")
        self.home_window.clearProperty("nimbus.search.input.trakt.encoded")
        xbmc.sleep(200)
        count_str = self.home_window.getProperty("nimbus.search.history.count")
        count = int(count_str) if count_str else 0
        if count == 0:
            self.home_window.setProperty("nimbus.search.history.empty", 
                                "Your search history is empty. Click the search icon to perform a new search.")
            xbmc.executebuiltin("SetFocus(802)")
        else:
            self.home_window.clearProperty("nimbus.search.history.empty")
            xbmc.executebuiltin("SetFocus(802)")

    def search_input(self, search_term=None, from_history=False):
        if search_term is None or not search_term.strip():
            prompt = "Search" if xbmcgui.getCurrentWindowId() == 10000 else "New Search"
            keyboard = xbmc.Keyboard("", prompt, False)
            keyboard.doModal()
            if keyboard.isConfirmed():
                search_term = keyboard.getText()
                if not search_term or not search_term.strip():
                    return
            else:
                return
        self.home_window.setProperty("nimbus.search.refreshing", "true")
        encoded_search_term = quote(search_term)
        existing_spath_id = self.check_spath_exists(search_term)
        if existing_spath_id:
            self.remove_spath_from_database(existing_spath_id)
        self.add_spath_to_database(search_term)
        existing_spath_id = self.check_spath_exists(search_term)
        self.update_search_history_properties(search_term, existing_spath_id)
        self.home_window.setProperty("nimbus.search.input", search_term)
        self.home_window.setProperty("nimbus.search.input.encoded", encoded_search_term)
        self.home_window.setProperty("nimbus.search.input.trakt.encoded", encoded_search_term)
        xbmc.sleep(200)
        if not from_history:
            xbmc.executebuiltin("SetFocus(2000)")
        xbmc.sleep(100)
        def load_widgets_and_clear_flag():
            xbmc.sleep(800)
            self.home_window.clearProperty("nimbus.search.refreshing")
        Thread(target=load_widgets_and_clear_flag).start()


    def re_search(self):
        search_term = xbmc.getInfoLabel("ListItem.Label")
        self.search_input(search_term, True)
        xbmc.sleep(100)
        xbmc.executebuiltin("SetFocus(9000,0,absolute)")
        xbmc.sleep(100)
        xbmc.executebuiltin("SetFocus(2000)")

    def toggle_search_provider(self):
        self.home_window.clearProperty("nimbus.search.input")
        self.home_window.clearProperty("nimbus.search.input.encoded")
        self.home_window.clearProperty("nimbus.search.input.trakt.encoded")
        current_provider = xbmc.getInfoLabel("Skin.String(current_search_provider)")
        if current_provider == "0":
            next_provider = "1"
        elif current_provider == "1":
            next_provider = "3"
        elif current_provider == "3":
            next_provider = "2"
        elif current_provider == "2":
            next_provider = "4"
        elif current_provider == "4":
            next_provider = "0"
        else:
            next_provider = "1"
        xbmc.executebuiltin(f"Skin.SetString(current_search_provider,{next_provider})")




# class SPaths:
#     def __init__(self, spaths=None):
#         self.connect_database()
#         if spaths is None:
#             self.spaths = []
#         else:
#             self.spaths = spaths
#         self.refresh_spaths = False

#     def connect_database(self):
#         if not xbmcvfs.exists(settings_path):
#             xbmcvfs.mkdir(settings_path)
#         self.dbcon = database.connect(spath_database_path, timeout=20)
#         self.dbcon.execute(
#             "CREATE TABLE IF NOT EXISTS spath (spath_id INTEGER PRIMARY KEY AUTOINCREMENT, spath text)"
#         )
#         self.dbcur = self.dbcon.cursor()

#     def add_spath_to_database(self, spath):
#         self.refresh_spaths = True
#         self.dbcur.execute(
#             "INSERT INTO spath (spath) VALUES (?)",
#             (spath,),
#         )
#         self.dbcon.commit()

#     def remove_spath_from_database(self, spath_id):
#         self.refresh_spaths = True
#         self.dbcur.execute("DELETE FROM spath WHERE spath_id = ?", (spath_id,))
#         self.dbcon.commit()

#     def is_database_empty(self):
#         self.dbcur.execute("SELECT COUNT(*) FROM spath")
#         rows = self.dbcur.fetchone()[0]
#         return rows == 0

#     def remove_all_spaths(self):
#         dialog = xbmcgui.Dialog()
#         title = "Nimbus"
#         prompt = "Are you sure you want to clear all search history? Once cleared, these items cannot be recovered. Proceed?"
#         self.fetch_all_spaths()
#         if dialog.yesno(title, prompt):
#             self.refresh_spaths = True
#             self.dbcur.execute("DELETE FROM spath")
#             self.dbcur.execute("DELETE FROM sqlite_sequence WHERE name='spath'")
#             self.dbcon.commit()
#             self.make_default_xml()
#             Thread(target=self.update_settings_and_reload_skin).start()

#     def fetch_all_spaths(self):
#         results = self.dbcur.execute(
#             "SELECT * FROM spath ORDER BY spath_id DESC"
#         ).fetchall()
#         return results

#     def update_settings_and_reload_skin(self):
#         xbmc.executebuiltin("Skin.SetString(SearchInput,)")
#         xbmc.executebuiltin("Skin.SetString(SearchInputEncoded,)")
#         xbmc.executebuiltin("Skin.SetString(SearchInputTraktEncoded, 'none')")
#         xbmc.executebuiltin("Skin.SetString(DatabaseStatus, 'Empty')")
#         xbmc.sleep(300)
#         xbmc.executebuiltin("ReloadSkin()")
#         xbmc.sleep(200)
#         xbmc.executebuiltin("SetFocus(27400)")

#     def make_search_history_xml(self, active_spaths, event=None):
#         if not self.refresh_spaths:
#             return
#         if not active_spaths:
#             self.make_default_xml()
#         xml_file = "special://skin/xml/%s.xml" % (search_history_xml)
#         final_format = xmls.media_xml_start.format(main_include="SearchHistory")
#         for _, spath in active_spaths:
#             body = xmls.history_xml_body
#             body = body.format(spath=spath)
#             final_format += body
#         final_format += xmls.media_xml_end
#         self.write_xml(xml_file, final_format)
#         xbmc.executebuiltin("ReloadSkin()")
#         if event is not None:
#             event.set()

#     def write_xml(self, xml_file, final_format):
#         with xbmcvfs.File(xml_file, "w") as f:
#             f.write(final_format)

#     def make_default_xml(self):
#         item = default_xmls["search_history"]
#         final_format = item[1].format(includes_type=item[2])
#         xml_file = "special://skin/xml/%s.xml" % item[0]
#         with xbmcvfs.File(xml_file, "w") as f:
#             f.write(final_format)

#     def check_spath_exists(self, spath):
#         result = self.dbcur.execute(
#             "SELECT spath_id FROM spath WHERE spath = ?", (spath,)
#         ).fetchone()
#         return result[0] if result else None

#     def open_search_window(self):
#         if xbmcgui.getCurrentWindowId() == 10000:
#             xbmc.executebuiltin("ActivateWindow(1121)")
#         if self.is_database_empty():
#             xbmc.executebuiltin("Skin.SetString(DatabaseStatus, 'Empty')")
#             xbmc.executebuiltin("Skin.SetString(SearchInputTraktEncoded, 'none')")
#             xbmc.executebuiltin("ReloadSkin()")
#             xbmc.sleep(200)
#             xbmc.executebuiltin("SetFocus(27400)")
#         else:
#             self.remake_search_history()
#             xbmc.executebuiltin("Skin.Reset(DatabaseStatus)")
#             xbmc.executebuiltin("Skin.SetString(SearchInput,)")
#             xbmc.executebuiltin("Skin.SetString(SearchInputEncoded,)")
#             xbmc.executebuiltin("Skin.SetString(SearchInputTraktEncoded, 'none')")
#             xbmc.executebuiltin("ReloadSkin()")
#             xbmc.sleep(200)
#             xbmc.executebuiltin("SetFocus(9000)")

#     def search_input(self, search_term=None):
#         if search_term is None or not search_term.strip():
#             prompt = "Search" if xbmcgui.getCurrentWindowId() == 10000 else "New Search"
#             keyboard = xbmc.Keyboard("", prompt, False)
#             keyboard.doModal()
#             if keyboard.isConfirmed():
#                 xbmc.executebuiltin("Skin.Reset(DatabaseStatus)")
#                 search_term = keyboard.getText()
#                 if not search_term or not search_term.strip():
#                     return
#             else:
#                 return
#         encoded_search_term = quote(search_term)
#         if xbmcgui.getCurrentWindowId() == 10000:
#             xbmc.executebuiltin("ActivateWindow(1121)")
#         existing_spath = self.check_spath_exists(search_term)
#         if existing_spath:
#             self.remove_spath_from_database(existing_spath)
#         self.add_spath_to_database(search_term)
#         if xbmcgui.getCurrentWindowId() == 10000:
#             self.make_search_history_xml(self.fetch_all_spaths())
#         else:
#             event = Event()
#             Thread(
#                 target=self.make_search_history_xml,
#                 args=(self.fetch_all_spaths(), event),
#             ).start()
#             event.wait()
#         xbmc.executebuiltin(f"Skin.SetString(SearchInputEncoded,{encoded_search_term})")
#         xbmc.executebuiltin(
#             f"Skin.SetString(SearchInputTraktEncoded,{encoded_search_term})"
#         )
#         xbmc.executebuiltin(f"Skin.SetString(SearchInput,{search_term})")
#         xbmc.executebuiltin("SetFocus(2000)")

#     def re_search(self):
#         search_term = xbmc.getInfoLabel("ListItem.Label")
#         self.search_input(search_term)

#     def remake_search_history(self):
#         self.refresh_spaths = True
#         active_spaths = self.fetch_all_spaths()
#         if active_spaths:
#             self.make_search_history_xml(active_spaths)
#         else:
#             self.make_default_xml()


# def remake_all_spaths(silent=False):
#     for item in "search_history":
#         SPaths(item).remake_search_history()
#     if not silent:
#         xbmcgui.Dialog().ok("Nimbus", "Search history remade")
