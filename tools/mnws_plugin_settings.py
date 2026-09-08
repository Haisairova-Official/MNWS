"""Schema-driven settings dialog for MNWS plugins."""
from __future__ import annotations

import string
import urllib.parse

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk, Pango


def validate_settings(values: dict) -> None:
    if values.get("api_mode") != "custom":
        return
    template = values.get("api_url", "").strip()
    if not template:
        raise ValueError("选择自定义 API 后，请填写地址。")
    allowed = {"id", "title", "artist", "album", "duration"}
    for _, field, spec, conversion in string.Formatter().parse(template):
        if field is not None and (field not in allowed or spec or conversion):
            raise ValueError("地址模板只支持 {id}、{title}、{artist}、{album} 和 {duration}。")
    parsed = urllib.parse.urlparse(template.format_map(dict.fromkeys(allowed, "test")))
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("API 地址必须是完整的 HTTP 或 HTTPS 地址。")


class SettingsDialog:
    def __init__(self, parent, name, schema, values):
        self.schema = schema
        self.values = dict(values)
        self.controls = {}
        self.dialog = Gtk.Dialog(title=name + "设置", transient_for=parent,
                                 modal=True, destroy_with_parent=True)
        self.dialog.set_default_size(620, 620)
        self.dialog.add_button("取消", Gtk.ResponseType.CANCEL)
        self.dialog.add_button("保存并应用", Gtk.ResponseType.OK)
        self.dialog.set_default_response(Gtk.ResponseType.OK)
        content = self.dialog.get_content_area()
        content.set_border_width(16)
        content.set_spacing(10)
        intro = Gtk.Label(label="字号随任务栏高度自动调整，原文与译文保持 3:2。", xalign=0)
        intro.set_line_wrap(True)
        content.pack_start(intro, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content.pack_start(scroll, True, True, 0)
        grid = Gtk.Grid(column_spacing=16, row_spacing=12)
        scroll.add(grid)
        row = 0
        for field in schema:
            key, kind = field["key"], field.get("type", "string")
            value = values.get(key, field.get("default", ""))
            label = Gtk.Label(label=field.get("label", key), xalign=0)
            label.set_line_wrap(True)
            label.set_max_width_chars(20)
            grid.attach(label, 0, row, 1, 1)
            if kind in ("font", "color"):
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                follow = Gtk.CheckButton(label="跟随主题")
                follow.set_active(not value)
                if kind == "font":
                    control = Gtk.FontButton()
                    control.set_show_size(False)
                    control.set_level(Gtk.FontChooserLevel.FAMILY)
                    if value:
                        control.set_font_name(str(value))
                else:
                    control = Gtk.ColorButton()
                    control.set_use_alpha(True)
                    rgba = Gdk.RGBA()
                    rgba.parse(str(value) if value else "#ffffff")
                    control.set_rgba(rgba)
                control.set_sensitive(bool(value))
                follow.connect("toggled", lambda toggle, target=control: target.set_sensitive(not toggle.get_active()))
                box.pack_start(control, True, True, 0)
                box.pack_start(follow, False, False, 0)
                widget = box
                self.controls[key] = (kind, control, follow)
            elif kind == "choice":
                control = Gtk.ComboBoxText()
                for choice, caption in field.get("choices", []):
                    control.append(choice, caption)
                control.set_active_id(str(value))
                widget = control
                self.controls[key] = (kind, control, None)
            elif kind == "number":
                control = Gtk.SpinButton.new_with_range(field.get("min", 0), field.get("max", 100), field.get("step", 1))
                control.set_value(float(value))
                widget = control
                self.controls[key] = (kind, control, None)
            else:
                control = Gtk.Entry()
                control.set_text(str(value))
                control.set_hexpand(True)
                widget = control
                self.controls[key] = (kind, control, None)
            widget.set_hexpand(True)
            grid.attach(widget, 1, row, 1, 1)
            row += 1
            if field.get("hint"):
                hint = Gtk.Label(label=field["hint"], xalign=0)
                hint.set_line_wrap(True)
                hint.set_max_width_chars(44)
                hint.get_style_context().add_class("dim-label")
                grid.attach(hint, 1, row, 1, 1)
                row += 1
        self.error = Gtk.Label(xalign=0)
        self.error.set_line_wrap(True)
        content.pack_start(self.error, False, False, 0)

    def collect(self):
        result = dict(self.values)
        for key, (kind, control, follow) in self.controls.items():
            if follow is not None and follow.get_active():
                result[key] = ""
            elif kind == "font":
                result[key] = Pango.FontDescription.from_string(control.get_font_name()).get_family()
            elif kind == "color":
                result[key] = control.get_rgba().to_string()
            elif kind == "choice":
                result[key] = control.get_active_id()
            elif kind == "number":
                result[key] = control.get_value_as_int()
            else:
                result[key] = control.get_text().strip()
        validate_settings(result)
        return result

    def run(self):
        self.dialog.show_all()
        while self.dialog.run() == Gtk.ResponseType.OK:
            try:
                result = self.collect()
            except ValueError as error:
                self.error.set_text(str(error))
                continue
            self.dialog.destroy()
            return result
        self.dialog.destroy()
        return None
