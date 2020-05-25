#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2020/5/20 20:00
# @Author  : RavagerWT
# @File    : language.py
# @Software: Visual Studio Code

import json

class Lang:

    def __init__(self, data) -> None:

        self.lang = data['lang']
        # GUI
        self.gui_title = data['GUI']['title']
        self.gui_program_setting = data['GUI']['program_setting']
        self.gui_setting_loaded = data['GUI']['setting_loaded']
        self.gui_load_setting_file = data['GUI']['load_setting_file']
        self.gui_settings_file = data['GUI']['settings_file']
        self.gui_apply_settings = data['GUI']['apply_settings']
        self.gui_open_setting_editor = data['GUI']['open_setting_editor']
        self.gui_file = data['GUI']['file']
        self.gui_load_file = data['GUI']['load_file']  # unused
        self.gui_result = data['GUI']['result']
        self.gui_exp_error_log = data['GUI']['exp_error_log']
        self.gui_exit = data['GUI']['exit']
        self.gui_success = data['GUI']['success']
        self.gui_fail = data['GUI']['fail']
        self.gui_ver = data['GUI']['ver']

        # GUI-settings
        self.st_author = data['settings']['author']
        self.st_check_update = data['settings']['check_update']
        self.st_website = data['settings']['website']
        self.st_setting_window_title = data['settings']['setting_window_title']
        self.st_localization = data['settings']['localization']
        self.st_gui_theme = data['settings']['gui_theme']
        self.st_ok = data['settings']['ok']
        self.st_cancel = data['settings']['cancel']

        # msg box
        self.msg_box_file_op_title = data['msg_box']['file_op_title']
        self.msg_box_file_not_exist = data['msg_box']['file_not_exist']
        self.msg_box_settings_file_not_change = data['msg_box']['settings_file_not_change']
        self.msg_box_date_fmt_wrong_title = data['msg_box']['date_fmt_wrong_title']
        self.msg_box_format_wrong = data['msg_box']['format_wrong']
        self.msg_box_chk_update_title = data['msg_box']['chk_update_title']
        self.msg_box_ver_up_to_date = data['msg_box']['ver_up_to_date']
        self.msg_box_need_update = data['msg_box']['need_update']
        self.msg_box_running_higher_ver_program = data['msg_box']['running_higher_ver_program']
        self.msg_box_running_unofficial_program = data['msg_box']['running_unofficial_program']
        self.msg_box_release_ver_not_exist = data['msg_box']['release_ver_not_exist']

        # aniGamerPlus
        self.ani_download_job_settings = data['aniGamerPlus']['download_job_settings']
        self.ani_check_latest_version = data['aniGamerPlus']['check_latest_version']
        self.ani_check_frequency = data['aniGamerPlus']['check_frequency']
        self.ani_read_sn_list_when_checking_update = data['aniGamerPlus']['read_sn_list_when_checking_update']
        self.ani_read_config_when_checking_update = data['aniGamerPlus']['read_config_when_checking_update']
        
        self.ani_file_storage_settings = data['aniGamerPlus']['file_storage_settings']
        self.ani_bangumi_dir = data['aniGamerPlus']['bangumi_dir']
        self.ani_temp_dir = data['aniGamerPlus']['temp_dir']
        self.ani_classify_bangumi = data['aniGamerPlus']['classify_bangumi']
        
        self.ani_download_settings = data['aniGamerPlus']['download_settings']
        self.ani_download_resolution = data['aniGamerPlus']['download_resolution']
        self.ani_lock_resolution = data['aniGamerPlus']['lock_resolution']
        self.ani_default_download_mode = data['aniGamerPlus']['default_download_mode']
        self.ani_download_mode_list_text = data['aniGamerPlus']['download_mode_list_text']
        self.ani_multi_thread = data['aniGamerPlus']['multi_thread']
        self.ani_multi_upload = data['aniGamerPlus']['multi_upload']
        self.ani_multi_downloading_segment = data['aniGamerPlus']['multi_downloading_segment']
        self.ani_segment_download_mode = data['aniGamerPlus']['segment_download_mode']
        self.ani_video_filename_extension = data['aniGamerPlus']['video_filename_extension']
        self.ani_audio_language_jpn = data['aniGamerPlus']['audio_language_jpn']
        
        self.ani_filename_settings = data['aniGamerPlus']['filename_settings']
        self.ani_add_bangumi_name_to_video_filename = data['aniGamerPlus']['add_bangumi_name_to_video_filename']
        self.ani_add_resolution_to_video_filename = data['aniGamerPlus']['add_resolution_to_video_filename']
        self.ani_zerofill = data['aniGamerPlus']['zerofill']
        self.ani_customized_video_filename_prefix = data['aniGamerPlus']['customized_video_filename_prefix']
        self.ani_customized_video_filename_suffix = data['aniGamerPlus']['customized_video_filename_suffix']
        self.ani_customized_bangumi_name_suffix = data['aniGamerPlus']['customized_bangumi_name_suffix']

if __name__ == '__main__':
    # open json file and read
    with open('lang_zhTW.json', 'r', encoding="utf-8") as reader:
        data = json.loads(reader.read())

    a = Lang(data)
    print(a.lang)
    print(a.gui_title)
    print(a.log_msg_description_keyword_missing)
    print(a.xls_sheet_names[3])
