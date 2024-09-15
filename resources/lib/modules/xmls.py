# -*- coding: utf-8 -*-

media_xml_start = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="{main_include}">'''

media_xml_end = '''
  </include>
</includes>'''

media_xml_body = '''
    <include content="{cpath_type}">
      <param name="content_path" value="{cpath_path}"/>
      <param name="widget_header" value="{cpath_header}"/>
      <param name="widget_target" value="videos"/>
      <param name="list_id" value="{cpath_list_id}"/>
    </include>'''

history_xml_body = '''
    <item>
      <label>$NUMBER[{spath}]</label>
      <onclick>RunScript(script.nimbus.helper,mode=re_search)</onclick>
    </item>'''

main_menu_movies_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="MoviesMainMenu">
    <item>
      <label>{cpath_header}</label>
      <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>
      <property name="menu_id">$NUMBER[19000]</property>
      <property name="id">movies</property>
      <visible>!Skin.HasSetting(HomeMenuNoMovieButton)</visible>
    </item>
  </include>
</includes>'''

main_menu_tvshows_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="TVShowsMainMenu">
    <item>
      <label>{cpath_header}</label>
      <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>
      <property name="menu_id">$NUMBER[22000]</property>
      <property name="id">tvshows</property>
      <visible>!Skin.HasSetting(HomeMenuNoTVShowButton)</visible>
    </item>
  </include>
</includes>'''

main_menu_custom1_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="Custom1MainMenu">
    <item>
      <label>{cpath_header}</label>
      <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>
      <property name="menu_id">$NUMBER[23000]</property>
      <property name="id">custom1</property>
      <visible>!Skin.HasSetting(HomeMenuNoCustom1Button)</visible>
    </item>
  </include>
</includes>'''

main_menu_custom2_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="Custom2MainMenu">
    <item>
      <label>{cpath_header}</label>
      <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>
      <property name="menu_id">$NUMBER[24000]</property>
      <property name="id">custom2</property>
      <visible>!Skin.HasSetting(HomeMenuNoCustom2Button)</visible>
    </item>
  </include>
</includes>'''

main_menu_custom3_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="Custom3MainMenu">
    <item>
      <label>{cpath_header}</label>
      <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>
      <property name="menu_id">$NUMBER[25000]</property>
      <property name="id">custom3</property>
      <visible>!Skin.HasSetting(HomeMenuNoCustom3Button)</visible>
    </item>
  </include>
</includes>'''

search_history_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="SearchHistory">
    <item>
      <label>{spath}</label>
      <onclick>RunScript(script.nimbus.helper,mode=re_search)</onclick>
    </item>
  </include>
</includes>'''

default_widget = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="{includes_type}">
  </include>
</includes>'''

default_main_menu = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="{includes_type}">
  </include>
</includes>'''

default_history = '''<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="{includes_type}">
  </include>
</includes>'''