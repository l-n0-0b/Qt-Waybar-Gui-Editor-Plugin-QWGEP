#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Name: qt waybar gui editor
# Author: l-n0-0b
# License: GNU GPL v2
#
# This program is free software.
# You may distribute and/or modify it according to the terms of the
# GNU General Public License versions 2.
#
################################################################

import sys, os, json, subprocess, glob, re
from backup_manager import show_backup_dialog
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

# Platform initialization fix for Wayland/X11 to work correctly
if "WAYLAND_DISPLAY" in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
else:
    os.environ["QT_QPA_PLATFORM"] = "xcb"

# Path constants
D_DIR = os.path.expanduser("~/.config/waybar")
P_DIR = os.path.join(D_DIR, "plugins")
D_CONF = os.path.join(D_DIR, "config.jsonc")
D_PINNED = os.path.join(D_DIR, "pinned.jsonc")
D_PLUGINS = os.path.join(D_DIR, "plugins.jsonc")
D_STYLE = os.path.join(D_DIR, "style.css")

# NEW Add the function itself (you can precede the class or inside as a method)
def load_config_safe(path):
    if not os.path.exists(path): return {}
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
        # Clean from comments that standard json does not understand
        clean = re.sub(r'//.*|/\*[\s\S]*?\*/', '', raw)
        return json.loads(clean)

class Waybar_Pro_Engine(QWidget):
    def __init__(self):
        super().__init__()
        # Initializing data stores
        self.reg, self.all_apps, self.tr, self.labels = {}, {}, {}, []
        self.plugin_checks = {}
        self.manual_icon_val = "application-x-executable"
        
        # Initial language definition (before UI creation)
        sys_l = os.environ.get('LANG', 'en')
        self.cur_lang = "rus" if "ru" in sys_l.lower() else "eng"
        
        for p in [D_DIR, P_DIR]: os.makedirs(p, exist_ok=True)
        
        # Initialization order
        self.init_ui()
        self.change_language_event(self.lang_box.currentText())
        self.load_system_apps()
        self.filter_apps()
        self.sync_config_fields()
        self.load_pinned()
        self.refresh_plugins_list()

    def close_app_force(self):
        """Method for complete and clean exit from the program"""
        # You can add a short pause or log if necessary
        print("Waybar Pro Engine: Closing application...")
        QApplication.quit()
        sys.exit(0)

    def _(self, k): 
        """Receiving a transfer"""
        return self.tr.get(k, k)

    def init_ui(self):
        """Creating a GUI"""
        self.resize(1150, 950)
        self.setStyleSheet("""
            QWidget { background: #2b303b; color: #f8f8f2; font-family: sans-serif; font-size: 13px; }
            QTabWidget::pane { border: 1px solid #4f5b66; background: #343d46; }
            QTabBar::tab { background: #4f5b66; padding: 10px 20px; margin-right: 2px; }
            QTabBar::tab:selected { background: #5e81ac; }
            QListWidget { background: #1e222a; border: 1px solid #4f5b66; outline: none; }
            QPushButton { background: #4f5b66; border-radius: 4px; padding: 10px; font-weight: bold; border: none; }
            QPushButton:hover { background: #5e81ac; }
            QLineEdit, QSpinBox, QComboBox { background: #1e222a; border: 1px solid #4f5b66; padding: 4px; color: white; }
        """)
        
        main_v = QVBoxLayout(self)

        # Choice of language
        lang_h = QHBoxLayout()
        lang_h.addStretch()
        self.lang_box = QComboBox()
        l_path = os.path.dirname(os.path.abspath(__file__))
        langs = [os.path.basename(f).replace('.jwaybar', '') for f in glob.glob(os.path.join(l_path, "*.jwaybar"))]
        if not langs: langs = ["eng", "rus"]
        self.lang_box.addItems(langs)
        self.lang_box.setCurrentText(self.cur_lang)
        self.lang_box.currentTextChanged.connect(self.change_language_event)
        lang_h.addWidget(QLabel("🌐"))
        lang_h.addWidget(self.lang_box)
        main_v.addLayout(lang_h)

        self.tabs = QTabWidget()
        
        # TAB 1: SETTINGS
        self.tab_gen = QWidget(); self.lay_gen = QFormLayout(self.tab_gen)
        sc_gen = QScrollArea(); sc_gen.setWidgetResizable(True); sc_gen.setWidget(self.tab_gen)
        self.tabs.addTab(sc_gen, "")

        # TAB 2: ATTACHMENTS
        self.tab_pinned = QWidget(); pin_v = QVBoxLayout(self.tab_pinned)
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.filter_apps)
        pin_v.addWidget(self.search_input)
        
        lists_h = QHBoxLayout()
        # Left side
        av_v = QVBoxLayout(); self.lbl_av = QLabel(); self.list_av = QListWidget()
        av_v.addWidget(self.lbl_av); av_v.addWidget(self.list_av); self.list_av.doubleClicked.connect(self.add_app)
        # Right side
        pin_v_col = QVBoxLayout(); self.lbl_pin = QLabel(); self.list_pin = QListWidget()
        pin_v_col.addWidget(self.lbl_pin); pin_v_col.addWidget(self.list_pin)
        self.list_pin.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_pin.itemDoubleClicked.connect(self.edit_pinned_app)
        
        lists_h.addLayout(av_v); lists_h.addLayout(pin_v_col)
        pin_v.addLayout(lists_h)
        
        # List control buttons
        btn_h = QHBoxLayout()
        self.btn_add_sel = QPushButton(); self.btn_add_sel.clicked.connect(self.add_app)
        self.btn_move_up = QPushButton("⬅️"); self.btn_move_up.clicked.connect(lambda: self.move_pinned_app(-1))
        self.btn_move_down = QPushButton("➡️"); self.btn_move_down.clicked.connect(lambda: self.move_pinned_app(1))
        self.btn_del_sel = QPushButton(); self.btn_del_sel.setStyleSheet("background: #bf616a;"); self.btn_del_sel.clicked.connect(self.remove_pinned_app)
        btn_h.addWidget(self.btn_add_sel); btn_h.addWidget(self.btn_move_up); btn_h.addWidget(self.btn_move_down); btn_h.addWidget(self.btn_del_sel)
        pin_v.addLayout(btn_h)

        # Manual addition
        manual_h = QHBoxLayout()
        self.manual_name = QLineEdit(); self.manual_cmd = QLineEdit()
        
        # Add an inscription in front of the icon button
        self.lbl_manual_icon = QLabel(self._('lang_manual_icon_label')) 
        
        self.manual_icon_btn = QPushButton()
        self.manual_icon_btn.setIcon(QIcon.fromTheme("image-x-generic"))
        self.manual_icon_btn.setFixedSize(40, 40)
        self.manual_icon_btn.clicked.connect(self.choose_manual_icon)
        
        self.btn_manual = QPushButton()
        self.btn_manual.clicked.connect(self.add_manual_app)
        
        manual_h.addWidget(self.manual_name)
        manual_h.addWidget(self.manual_cmd)
        manual_h.addWidget(self.lbl_manual_icon) # inscription
        manual_h.addWidget(self.manual_icon_btn)
        manual_h.addWidget(self.btn_manual)
        pin_v.addLayout(manual_h)

        self.tabs.addTab(self.tab_pinned, "")

        # TAB 3: PLUGINS
        self.tab_plugins = QWidget()
        self.plugin_lay = QVBoxLayout(self.tab_plugins)

        # Open directory button via QDesktopServices (correct Qt path) (NO WORK)
        #self.btn_open_plugins = QPushButton(self._('open_plugins'))
        # We use QUrl.fromLocalFile to correctly handle paths with spaces
        #self.btn_open_plugins.clicked.connect(self.open_plugin_folder)
        
        # 1. Inscription from localization (Open plugins folder)
        self.btn_open_plugins = QLabel(self._('open_plugins'))
        self.plugin_lay.addWidget(self.btn_open_plugins)

        # 2. Line with path that can be copied
        self.path_edit = QLineEdit(P_DIR)
        self.path_edit.setReadOnly(True)  # Read-only to avoid accidentally erasing the path
       #self.path_edit.setStyleSheet("background: transparent; border: 1px solid #555; padding: 5px;")
        # Настраиваем стиль всплывающего облачка (цвета Nord)
        self.path_edit.setStyleSheet("""
            QLineEdit { background: transparent; border: 1px solid #555; padding: 5px; }
            QToolTip { color: #ffffff; background-color: #2e3440; border: 1px solid #81a1c1; }
        """)
        self.path_edit.setPlaceholderText("Plugin Path...")
         # Устанавливаем всплывающую подсказку при наведении мыши
       #self.path_edit.setToolTip(self._('tooltip_copy_path'))
        self.path_edit.setToolTip(f"<div style='color: #ffffff; background-color: #333333; padding: 5px;'>{self._('tooltip_copy_path')}</div>")
         # Или просто текстом, если в локализации нет ключа:
       #self.path_edit.setToolTip("Выделите и скопируйте путь (Ctrl+C) для вставки в проводник")
        self.plugin_lay.addWidget(self.path_edit)

        # Next, your container with a list
        self.plugin_container = QWidget()
        self.plugin_scroll_lay = QVBoxLayout(self.plugin_container)
        sc_pl = QScrollArea()
        sc_pl.setWidgetResizable(True)
        sc_pl.setWidget(self.plugin_container)
        self.plugin_lay.addWidget(sc_pl)
        
        self.tabs.addTab(self.tab_plugins, "")

        main_v.addWidget(self.tabs)
        
        bottom_h = QHBoxLayout()
        
        # Main save button
        self.b_save = QPushButton()
        self.b_save.setFixedHeight(55)
        self.b_save.clicked.connect(self.run_save)
        
        # New exit button
        self.btn_exit = QPushButton("❌") # Icon translation
        self.btn_exit.setFixedWidth(100)
        self.btn_exit.setFixedHeight(55)
        self.btn_exit.setStyleSheet("background: #bf616a;") # Red color
        self.btn_exit.clicked.connect(self.close_app_force)
        
        bottom_h.addWidget(self.b_save, 7) # Save button wider
        bottom_h.addWidget(self.btn_exit, 1) # Exit button thinner
        main_v.addLayout(bottom_h)

    def change_language_event(self, lang_name):
        """Dictionary change and UI update"""
        self.cur_lang = lang_name
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{self.cur_lang}.jwaybar")
        if os.path.exists(p):
            self.tr = {}
            with open(p, 'r', encoding='utf-8') as f:
                for ln in f:
                    if '=' in ln and not ln.startswith('#'):
                        k, v = map(str.strip, ln.split('=', 1))
                        self.tr[k] = v
            self.update_ui_texts()

    def update_ui_texts(self):
        """Update all interface texts"""
        self.setWindowTitle(self._('title'))
        for k, lbl in self.labels: lbl.setText(self._(k))
        self.lbl_av.setText(self._('lang_name_win_programs_add'))
        self.lbl_pin.setText(self._('lang_name_win_programs_edit'))
        self.search_input.setPlaceholderText(self._('search_placeholder'))
        self.b_save.setText(self._('btn_save'))
        self.btn_add_sel.setText("➕ " + self._('btn_add'))
        self.btn_del_sel.setText("🗑 " + self._('btn_rem'))
        self.btn_manual.setText("➕ " + self._('btn_add_manual'))
        self.lbl_manual_icon.setText(self._('lang_manual_icon_label'))
        self.manual_name.setPlaceholderText("Name")
        self.manual_cmd.setPlaceholderText("Command")
        self.tabs.setTabText(0, self._('tab_gen'))
        self.tabs.setTabText(1, self._('tab_pinned'))
        self.tabs.setTabText(2, self._('tab_plugins'))
        self.btn_open_plugins.setText(self._('open_plugins')) #NEW
        self.path_edit.setToolTip(self._('tooltip_copy_path')) #NEW
        self.btn_exit.setText(self._('btn_exit_text'))

    def load_system_apps(self):
        """Scanning programs"""
        self.all_apps = {}
        paths = ['/usr/share/applications/*.desktop', os.path.expanduser('~/.local/share/applications/*.desktop')]
        for path in paths:
            for file in glob.glob(path):
                try:
                    n, c, ic = None, None, None
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if line.startswith('Name='): n = line.split('=')[-1].strip()
                            if line.startswith('Exec='): c = line.split('=')[-1].split('%')[0].replace('"', '').strip()
                            if line.startswith('Icon='): ic = line.split('=')[-1].strip()
                    if n and c: self.all_apps[n] = {'cmd': c, 'icon': ic or "application-x-executable"}
                except: continue

    def choose_manual_icon(self):
        """Icon selection"""
        f_p, _ = QFileDialog.getOpenFileName(self, "Icon", "/usr/share/icons", "Images (*.png *.svg *.jpg);;All Files (*)")
        if f_p:
            self.manual_icon_val = f_p
            self.manual_icon_btn.setIcon(QIcon(f_p))

    def pick_color(self, line_edit):
        """Color selection dialog"""
        color = QColorDialog.getColor()
        if color.isValid(): line_edit.setText(color.name())

    def add_manual_app(self):
        """Add Custom Program"""
        name, cmd = self.manual_name.text().strip(), self.manual_cmd.text().strip()
        if not cmd: return
        ic_src = self.manual_icon_val
        ic = QIcon(ic_src) if os.path.exists(ic_src) else QIcon.fromTheme(ic_src)
        it = QListWidgetItem(ic, name or cmd)
        it.setData(Qt.ItemDataRole.UserRole, {'cmd': cmd, 'icon': ic_src})
        self.list_pin.addItem(it)
        self.manual_name.clear(); self.manual_cmd.clear(); self.manual_icon_val = "application-x-executable"
        self.manual_icon_btn.setIcon(QIcon.fromTheme("image-x-generic"))

    def edit_pinned_app(self, item):
        """Double-click editing"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.manual_name.setText(item.text())
            self.manual_cmd.setText(data.get('cmd', ''))
            self.manual_icon_val = data.get('icon', 'application-x-executable')
            ic = QIcon(self.manual_icon_val) if os.path.exists(self.manual_icon_val) else QIcon.fromTheme(self.manual_icon_val)
            self.manual_icon_btn.setIcon(ic)
            self.list_pin.takeItem(self.list_pin.row(item))

    def move_pinned_app(self, direction):
        """Offset up/down"""
        row = self.list_pin.currentRow()
        new_row = row + direction
        if 0 <= new_row < self.list_pin.count():
            item = self.list_pin.takeItem(row)
            self.list_pin.insertItem(new_row, item)
            self.list_pin.setCurrentRow(new_row)

    def filter_apps(self):
        """List Search"""
        q = self.search_input.text().lower(); self.list_av.clear()
        for n in sorted(self.all_apps.keys()):
            if q in n.lower():
                it = QListWidgetItem(QIcon.fromTheme(self.all_apps[n]['icon']), n)
                it.setData(Qt.ItemDataRole.UserRole, self.all_apps[n]); self.list_av.addItem(it)

    def add_app(self):
        """Add from available list"""
        src = self.list_av.currentItem()
        if src:
            it = QListWidgetItem(src.icon(), src.text())
            it.setData(Qt.ItemDataRole.UserRole, src.data(Qt.ItemDataRole.UserRole)); self.list_pin.addItem(it)

    def remove_pinned_app(self):
        """Remove from selected list"""
        for item in self.list_pin.selectedItems(): self.list_pin.takeItem(self.list_pin.row(item))

    def sync_config_fields(self):
        """Set up dynamic fields"""
        base = {
            'position': 'top', 'height': '30', 'spacing': '4',
            'bg_color': '#2b303b', 'bg_opacity': '100', 'main_color': '#f8f8f2',
            'margin-top': '0', 'margin-bottom': '0', 'margin-left': '0', 'margin-right': '0',
            'cl_format': ' {:%H:%M}', 'cl_tooltip-format': '{:%Y-%m-%d}',
            'au_format': '{icon} {volume}%', 'nw_format-wifi': ' {essid}',
            'bat_format': '{icon} {capacity}%', 'cpu_format': ' {usage}%', 'mem_format': ' {}%', 'task_icon-size': '20', 
'tray_spacing': '10'
        }
        mod_m = {"cl":"clock", "au":"pulseaudio", "nw":"network", "bat":"battery", "cpu":"cpu", "mem":"memory", "tray":"tray"}
        
        d = load_config_safe(D_CONF)
        if d:
            try:
                for k in base:
                    p, key = (k.split('_', 1) if '_' in k else (None, k))
                    mod = mod_m.get(p)
                    # Added isinstance check to avoid falling on empty modules
                    if mod and mod in d and isinstance(d[mod], dict) and key in d[mod]: 
                        base[k] = str(d[mod][key])
                    elif k in d: 
                        base[k] = str(d[k])
            except Exception as e:
                print(f"Sync fields error: {e}")

        for k, v in base.items():
            h, chk = QHBoxLayout(), QCheckBox(); chk.setChecked(True)
            if 'color' in k:
                ctrl = QLineEdit(v); btn = QPushButton("🎨"); btn.setFixedWidth(40)
                btn.clicked.connect(lambda checked, e=ctrl: self.pick_color(e))
                h.addWidget(ctrl); h.addWidget(btn)
            elif k == 'position':
                ctrl = QComboBox(); ctrl.addItems(['top', 'bottom', 'left', 'right']); ctrl.setCurrentText(v); h.addWidget(ctrl)
            elif v.replace('-','').isdigit():
                val = int(v); ctrl = QSpinBox(); ctrl.setRange(-100, 1000); ctrl.setValue(val)
                sld = QSlider(Qt.Orientation.Horizontal); sld.setRange(0, 100); sld.setValue(min(max(val, 0), 100))
                ctrl.valueChanged.connect(sld.setValue); sld.valueChanged.connect(ctrl.setValue)
                h.addWidget(ctrl); h.addWidget(sld)
            else:
                ctrl = QLineEdit(v); h.addWidget(ctrl)
            lbl = QLabel(self._(k)); self.labels.append((k, lbl))
            h.insertWidget(0, chk); self.lay_gen.addRow(lbl, h); self.reg[k] = (chk, ctrl)

    def resolve_icon(self, name):
        """Find icon path"""
        if os.path.exists(name): return name
        for p in [f"/usr/share/icons/hicolor/48x48/apps/{name}.png", f"/usr/share/icons/hicolor/scalable/apps/{name}.svg", f"/usr/share/pixmaps/{name}.png"]:
            if os.path.exists(p): return p
        return ""

    def run_save(self):
        # We pass self._ so that the manager can "speak" in the selected language
        if not show_backup_dialog(self, D_DIR, self._):
            return
        
        try:
            """Save and apply settings"""
            # Collecting plugins
            p_cfg = {}
            for fn, chk in self.plugin_checks.items():
                if chk.isChecked():
                    p_data = load_config_safe(os.path.join(P_DIR, fn))
                    if p_data: p_cfg.update(p_data)

            with open(D_PLUGINS, 'w', encoding='utf-8') as f: json.dump(p_cfg, f, indent=4, ensure_ascii=False)

            # CSS Generation (Opacity enabled)
            bg_hex = self.reg['bg_color'][1].text() if 'bg_color' in self.reg else "#2b303b"
            op_val = int(self.reg['bg_opacity'][1].value()) if 'bg_opacity' in self.reg else 100
            fg = self.reg['main_color'][1].text() if 'main_color' in self.reg else "#f8f8f2"
            
            q_clr = QColor(bg_hex)
            rgba = f"rgba({q_clr.red()}, {q_clr.green()}, {q_clr.blue()}, {op_val/100.0})"
            css = f"/* Generated Style */\n#waybar {{ background: {rgba}; color: {fg}; }}\n"
            # Add to the css variable:
            css += "\n#custom-separator { color: #4f5b66; margin: 0 5px; padding-bottom: 2px; }\n"
            css += "#taskbar button { padding: 0 5px; border-bottom: 2px solid transparent; }\n"
            css += "#taskbar button.active { border-bottom: 2px solid #5e81ac; background: rgba(255,255,255,0.1); }\n"

            pin_j = {"group/pinned": {"orientation": "horizontal", "modules": []}}
            for i in range(self.list_pin.count()):
                it = self.list_pin.item(i); d = it.data(Qt.ItemDataRole.UserRole); m_id = f"pin-{i}"
                pin_j["group/pinned"]["modules"].append(f"custom/{m_id}")
                cmd_esc = d['cmd'].replace("'", "'\\''")
                pin_j[f"custom/{m_id}"] = {"format": " ", "on-click": f"sh -c '{cmd_esc}'" if cmd_esc else "true", "tooltip-format": it.text()}
                icon_path = self.resolve_icon(d['icon'])
                css += f'#custom-{m_id} {{ background-image: url("{icon_path}"); background-size: 22px; min-width: 32px; min-height: 28px; background-repeat: no-repeat; background-position: center; }}\n'
            
            with open(D_PINNED, 'w', encoding='utf-8') as f: json.dump(pin_j, f, indent=4, ensure_ascii=False)

            # Collecting a list of modules from all INCLUDED plugins
            custom_modules = []
            for fn, chk in self.plugin_checks.items(): #NEW
                if chk.isChecked():
                    plugin_data = load_config_safe(os.path.join(P_DIR, fn))
                    if plugin_data:
                        custom_modules.extend(plugin_data.keys())

            # Forming a config with a separator and a taskbar
            final_cfg = {
                "include": [D_PINNED, D_PLUGINS],
                "modules-left": ["wlr/workspaces", "group/pinned", "custom/separator", "wlr/taskbar"],
                "modules-right": custom_modules + ["tray", "cpu", "memory", "pulseaudio", "network", "battery", "clock"],
                
                # Setting the separator
                "custom/separator": {
                    "format": "|",
                    "tooltip": False
                },
                
                # Setting the list of running windows
                "wlr/taskbar": {
                    "format": "{icon}",
                    "icon-size": int(self.reg['task_icon-size'][1].value()) if 'task_icon-size' in self.reg else 20,
                    "tooltip-format": "{title}",
                    "on-click": "activate",
                    "on-click-middle": "close",
                    "ignore-list": [] # You can hide unneeded windows
                },
                
                "wlr/workspaces": {"on-click": "activate"}
            }
            mod_m = {"cl":"clock", "au":"pulseaudio", "nw":"network", "bat":"battery", "cpu":"cpu", "mem":"memory", "tray":"tray"}

            
            for k, (chk, ctrl) in self.reg.items():
                if not chk.isChecked(): continue
                val = ctrl.currentText() if isinstance(ctrl, QComboBox) else (ctrl.value() if isinstance(ctrl, QSpinBox) else ctrl.text())
                if '_' in k:
                    p, key = k.split('_', 1); mod = mod_m.get(p)
                    if mod:
                        if mod not in final_cfg: final_cfg[mod] = {}
                        final_cfg[mod][key] = val
                else: final_cfg[k] = val

            with open(D_CONF, 'w', encoding='utf-8') as f: json.dump(final_cfg, f, indent=4, ensure_ascii=False)
            with open(D_STYLE, 'w', encoding='utf-8') as f: f.write(css)

            subprocess.run(['killall', 'waybar'], stderr=subprocess.DEVNULL)
            subprocess.Popen(['waybar', '-c', D_CONF, '-s', D_STYLE], start_new_session=True)
            self.b_save.setText("✅ OK"); QTimer.singleShot(1500, lambda: self.b_save.setText(self._('btn_save')))
        except Exception as e: QMessageBox.critical(self, "Error", f"Save failed: {str(e)}")

    def refresh_plugins_list(self):
        """Updating plugin list"""
        while self.plugin_scroll_lay.count():
            w = self.plugin_scroll_lay.takeAt(0).widget()
            if w: w.deleteLater()
        self.plugin_checks = {}
        for f in glob.glob(os.path.join(P_DIR, "*.json")):
            fn = os.path.basename(f); chk = QCheckBox(fn); chk.setChecked(True); self.plugin_checks[fn] = chk; self.plugin_scroll_lay.addWidget(chk)
        self.plugin_scroll_lay.addStretch()

    def load_pinned(self): #NEW UPDATE
        """Loading pinned applications"""
        d = load_config_safe(D_PINNED)
        if not d: return
        try:
            for m in d.get("group/pinned", {}).get("modules", []):
                if m not in d: continue # Checking for a key
                cmd = d[m].get("on-click", "").replace("sh -c '", "")[:-1].replace("'\\''", "'")
                name = d[m].get("tooltip-format", cmd)
                meta = next((v for v in self.all_apps.values() if v['cmd'] == cmd), {'icon': 'application-x-executable'})
                it = QListWidgetItem(QIcon.fromTheme(meta['icon']), name)
                it.setData(Qt.ItemDataRole.UserRole, {'cmd': cmd, 'icon': meta['icon']}); self.list_pin.addItem(it)
        except Exception as e: 
            print(f"Error loading pinned: {e}")


if __name__ == "__main__": #exit
    app = QApplication(sys.argv); ex = Waybar_Pro_Engine(); ex.show(); sys.exit(app.exec())
