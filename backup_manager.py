#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Name: qt waybar gui editor add ico buttom
# Author: l-n0-0b
# License: GNU GPL v2
#
# This program is free software.
# You may distribute and/or modify it according to the terms of the
# GNU General Public License versions 2.
#
################################################################

import os
import shutil
from datetime import datetime  # Add date
from PyQt6.QtWidgets import QMessageBox

def show_backup_dialog(parent, d_dir, tr_func):
    """Диалог бэкапа без парсинга JSON (только копирование)"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(tr_func('title'))
    msg.setIcon(QMessageBox.Icon.Warning)
    # We take texts from key translation files
    msg.setText(tr_func('msg_save_warn'))
    msg.setInformativeText(tr_func('msg_backup_ask'))
    # Buttons with names from translation
    btn_backup = msg.addButton(tr_func('btn_backup_action'), QMessageBox.ButtonRole.ActionRole)
    btn_ok = msg.addButton("ОК", QMessageBox.ButtonRole.AcceptRole)
    btn_cancel = msg.addButton(tr_func('btn_cancel'), QMessageBox.ButtonRole.RejectRole)
    
    msg.exec()
    
    clicked = msg.clickedButton()
    
    if clicked == btn_backup:
        try:
            # Forming a time stamp: YYYYMMMDD-HHMMSS
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            # Create a path of the form/path/to/dir.backup-YYYYMMMDD-HHMMSS
            backup_path = f"{d_dir.rstrip('/')}.backup-{timestamp}"
            shutil.copytree(d_dir, backup_path)
            return True 
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Backup failed: {str(e)}")
            return False
            
    return clicked == btn_ok
