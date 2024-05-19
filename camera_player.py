from kivymd.uix.screen import Screen
from kivymd.uix.list import TwoLineAvatarIconListItem


class CamPlayer(Screen):
    current_cam: TwoLineAvatarIconListItem
    cam_id: int
