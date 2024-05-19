from kivymd.uix.imagelist import SmartTileWithLabel
from kivymd.uix.behaviors import TouchBehavior
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton


class PresetViewer(SmartTileWithLabel, TouchBehavior):
    def __init__(self):
        super().__init__()
        self._long_touch = False
        self.dialog = None
        self.delete_preset = None
        self.run_preset = None

    def on_long_touch(self, *args):
        self._long_touch = True
        if not self.dialog:
            self.dialog = MDDialog(
                text="Delete preset?",
                size_hint_y=None,
                padding=10,
                buttons=[
                    MDFlatButton(
                        text="DELETE",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda x: self._del_preset()
                    ),
                    MDFlatButton(
                        text="CANCEL",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda x: self.dialog.dismiss()
                    ),
                ],
            )
        self.dialog.open()

    def _del_preset(self):
        if self.delete_preset:
            self.delete_preset(int(super().id), self)
        self.dialog.dismiss()

    def on_release(self):
        if not self._long_touch:
            self._run_preset()
        else:
            self._long_touch = False

    def _run_preset(self):
        if self.run_preset:
            self.run_preset(int(super().id), self)
