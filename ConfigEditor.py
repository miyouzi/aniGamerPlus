#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2020/5/20 20:00
# @Author  : RavagerWT
# @File    : ConfigEditor.py
# @Software: Visual Studio Code

import os
import json
import ctypes
import webbrowser
import PySimpleGUI as sg
import Config
import language
from aniGamerPlus import check_new_version

def __init_settings(gui_path):
    if os.path.exists(gui_path):
        os.remove(gui_path)
    settings = {
                'ver': 0,
                'gui_lang': '繁體中文 台灣 (zhTW)',
                'ava_lang_for_GUI': [
                    '简体中文 (zhCN)',
                    '繁體中文 台灣 (zhTW)'
                ],
                'gui_theme': 'DarkTeal10',
                'set_lang': '繁體中文 台灣 (zhTW)'
                }
    with open(gui_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
    
# load GUI setting from gui_settings.json
def load_gui_settings(gui_setting_file_name = 'gui_settings.json'):
    # open json file and read
    gui_setting_exist = True
    if not os.path.exists(gui_setting_file_name):
        __init_settings(gui_setting_file_name)
        gui_setting_exist = False
    with open(gui_setting_file_name, 'r', encoding="utf-8") as setting:
        my_setting = json.loads(setting.read())
    return my_setting, gui_setting_exist

# load langage from lang.json
def loadLang(lang_code='繁體中文 台灣 (zhTW)'):
    lang_file_name = 'lang_' + lang_code[-5:-1] + '.json'
    # open json file and read
    if os.path.exists(lang_file_name):
        with open(lang_file_name, 'r', encoding="utf-8") as lang:
            lang_setting = json.loads(lang.read())
        return language.Lang(lang_setting)
    else:
        MessageBox(None, lang_file_name + ' ' + '檔案不存在!', '檔案操作', 0)

def save_settings(config_path, settings):
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

def save_gui_settings(gui_path, gui_settings):
    with open(gui_path, 'w', encoding='utf-8') as f:
        json.dump(gui_settings, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    working_dir = os.path.dirname(os.path.realpath(__file__))
    MessageBox = ctypes.windll.user32.MessageBoxW  

    # get gui configuration
    gui_path = os.path.join(working_dir, 'gui_settings.json')
    gui_settings, gui_setting_exist = load_gui_settings(gui_path)
    gui_lang = gui_settings['gui_lang']
    ava_lang_for_GUI = gui_settings['ava_lang_for_GUI']
    gui_theme = gui_settings['gui_theme']    

    config_path = os.path.join(working_dir, 'config.json')
    settings = Config.read_settings()
    default_download_mode_list = ['latest','all','latest-sn']
    
    render_windows = True
    while render_windows:
        # GUI layout
        sg.change_look_and_feel(gui_theme)  # windows colorful
        lang = loadLang(gui_lang)
        if gui_setting_exist == False:
            MessageBox(None, lang.msg_box_file_not_exist, lang.msg_box_file_op_title, 0)
            gui_setting_exist = True
        layout = [
            [sg.Button(lang.st_check_update, key='check update'), sg.Button(lang.st_website, key='website')],
            [sg.Text('_' * 100, size=(55, 1))],
            [sg.Text(lang.st_localization), sg.InputCombo(ava_lang_for_GUI, size=(
                20, 1),enable_events=True, default_value=gui_lang, key='set_lang', readonly=True)],
            [sg.Text(lang.st_gui_theme + ': '), sg.InputCombo(sg.list_of_look_and_feel_values(), size=(
                20, 1), default_value=gui_theme, enable_events=True, key='gui_theme', readonly=True)],
            [sg.Text('_' * 100, size=(55, 1))],
            [sg.Text(lang.ani_download_job_settings+'：')],
            [sg.Checkbox(lang.ani_check_latest_version,default=settings['check_latest_version'],key='check_latest_version'),
            sg.Text(lang.ani_check_frequency+'：'),sg.InputCombo([i for i in range(5,125,5)],default_value=settings['check_frequency'],key='check_frequency')],
            [sg.Checkbox(lang.ani_read_sn_list_when_checking_update,default=settings['read_sn_list_when_checking_update'],key='read_sn_list_when_checking_update'),
            sg.Checkbox(lang.ani_read_config_when_checking_update,default=settings['read_config_when_checking_update'],key='read_config_when_checking_update')],
            [sg.Text('_' * 100, size=(55, 1))],
            [sg.Text(lang.ani_file_storage_settings + '：')],
            [sg.Text(lang.ani_bangumi_dir + '：'), sg.Text(text=settings['bangumi_dir'], size=(40, 1), key='bangumi_dir_text')],
            [sg.Text(lang.ani_temp_dir + '：'), sg.Text(text=settings['temp_dir'], size=(40, 1), key='temp_dir_text')],
            [sg.FolderBrowse(lang.ani_bangumi_dir, target='bangumi_dir_text', key='bangumi_dir'), 
            sg.FolderBrowse(lang.ani_temp_dir, target='temp_dir_text', key='temp_dir'), sg.Checkbox(text=lang.ani_classify_bangumi, default=settings['classify_bangumi'], key='classify_bangumi')],
            [sg.Text('_' * 100, size=(55, 1))],
            [sg.Text(lang.ani_download_settings + '：')],
            [sg.Text(lang.ani_download_resolution + '：'), sg.InputCombo([1080,720,540,360], default_value=settings['download_resolution'], key='download_resolution', readonly=True),
             sg.Checkbox(text=lang.ani_lock_resolution, default=settings['lock_resolution'], key='lock_resolution')],
            [sg.Text(lang.ani_default_download_mode + '：'), 
            sg.InputCombo(lang.ani_download_mode_list_text, default_value=lang.ani_download_mode_list_text[default_download_mode_list.index(settings['default_download_mode'])],size=(15,1),key='default_download_mode', readonly=True)],
            [sg.Text(lang.ani_multi_thread + '：'), sg.InputCombo([1,2,3,4,5],default_value=settings['multi-thread'],key='multi-thread',readonly=True),
            sg.Text(lang.ani_multi_upload + '：'), sg.InputCombo([1,2,3],default_value=settings['multi_upload'],key='multi_upload',readonly=True)],
            [sg.Text(lang.ani_multi_downloading_segment + '：'), sg.InputCombo([1,2,3,4,5],default_value=settings['multi_downloading_segment'],key='multi_downloading_segment',readonly=True),
             sg.Checkbox(lang.ani_segment_download_mode,default=settings['segment_download_mode'],key='segment_download_mode')],
            [sg.Text(lang.ani_video_filename_extension + '：'), sg.InputCombo(['mp4','mkv','ts','mov'],default_value=settings['video_filename_extension'],size=(4,1),key='video_filename_extension',readonly=True),
            sg.Checkbox(lang.ani_audio_language_jpn,default=settings['audio_language_jpn'],key='audio_language_jpn')],
            [sg.Text('_' * 100, size=(55, 1))],
            [sg.Text(lang.ani_filename_settings + '：')],
            [sg.Checkbox(lang.ani_add_bangumi_name_to_video_filename,default=settings['add_bangumi_name_to_video_filename'],key='add_bangumi_name_to_video_filename'),
            sg.Checkbox(lang.ani_add_resolution_to_video_filename,default=settings['add_resolution_to_video_filename'],key='add_resolution_to_video_filename')],
            [sg.Text(lang.ani_zerofill+'：'), sg.Slider(range=(0, 100), orientation='h',size=(35, 20),default_value=settings['zerofill'], key='zerofill')],
            [sg.Text(lang.ani_customized_video_filename_prefix + '：'), sg.Input(default_text=settings['customized_video_filename_prefix'], key='customized_video_filename_prefix')],
            [sg.Text(lang.ani_customized_video_filename_suffix + '：'), sg.Input(default_text=settings['customized_video_filename_suffix'], key='customized_video_filename_suffix')],
            [sg.Text(lang.ani_customized_bangumi_name_suffix + '：'), sg.Input(default_text=settings['customized_bangumi_name_suffix'], key='customized_bangumi_name_suffix')],
            [sg.Text('_' * 100, size=(55, 1))],
            [sg.Button(button_text=lang.gui_apply_settings, key='Apply'), sg.Button(button_text=lang.gui_exit, key='Exit')]
        ]
        
        window = sg.Window(lang.st_setting_window_title, auto_size_text=True,
                    default_element_size=(40, 10)).Layout(layout)

        # process GUI event
        continue_program = True
        while continue_program:
            event, values = window.Read()
            print('event: ', event, '\nvalues:', values)  # debug message
            if event == 'Apply':
                settings['check_latest_version'] = values['check_latest_version']
                settings['check_frequency'] = values['check_frequency']
                settings['read_sn_list_when_checking_update'] = values['read_sn_list_when_checking_update']
                settings['read_config_when_checking_update'] = values['read_config_when_checking_update']
                settings['bangumi_dir'] = values['bangumi_dir']
                settings['temp_dir'] = values['temp_dir']
                settings['classify_bangumi'] = values['classify_bangumi']
                settings['download_resolution'] = values['download_resolution']
                settings['lock_resolution'] = values['lock_resolution']
                settings['default_download_mode'] = default_download_mode_list[lang.ani_download_mode_list_text.index(values['default_download_mode'])]
                settings['multi-thread'] = values['multi-thread']
                settings['multi_upload'] = values['multi_upload']
                settings['multi_downloading_segment'] = values['multi_downloading_segment']
                settings['segment_download_mode'] = values['segment_download_mode']
                settings['add_bangumi_name_to_video_filename'] = values['add_bangumi_name_to_video_filename']
                settings['add_resolution_to_video_filename'] = values['add_resolution_to_video_filename']
                settings['zerofill'] = values['zerofill']
                settings['customized_video_filename_prefix'] = values['customized_video_filename_prefix']
                settings['customized_video_filename_suffix'] = values['customized_video_filename_suffix']
                settings['customized_bangumi_name_suffix'] = values['customized_bangumi_name_suffix']
                settings['video_filename_extension'] = values['video_filename_extension']
                settings['audio_language_jpn'] = values['audio_language_jpn']
                # save configuration
                save_settings(config_path, settings)
            elif event == 'check update':
                if settings['check_latest_version']:
                    check_new_version(settings)  # 检查新版
                    version_msg = '當前aniGamerPlus版本: ' + \
                        settings['aniGamerPlus_version']
                    MessageBox(None, version_msg, '檢查更新', 0)
            elif event == 'website':
                webbrowser.open('https://github.com/miyouzi/aniGamerPlus')
            elif event == 'gui_theme':
                window.Close()
                gui_theme = values['gui_theme']
                save_gui_settings(gui_path, gui_settings)
                continue_program = False
            elif event == 'set_lang':
                window.Close()
                gui_lang = values['set_lang']
                save_gui_settings(gui_path, gui_settings)
                continue_program = False
            elif event is None or event == 'Exit':
                window.Close()
                continue_program = False
                render_windows = False
