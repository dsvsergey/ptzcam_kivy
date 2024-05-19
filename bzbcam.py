from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.imagelist import SmartTileWithLabel, SmartTile
from kivy.core.image import Image
from kivymd.uix.list import TwoLineAvatarIconListItem, IconLeftWidget, \
    OneLineAvatarIconListItem, ImageLeftWidget, ThreeLineRightIconListItem
from kivymd.uix.screen import Screen
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.tab import MDTabsBase
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.behaviors import TouchBehavior
import cv2
import numpy as np
import math
import pickle
import os.path
import os

from visca.visca import ViscaClient
from models import session, Camera, Preset
from utls import rtsp_builder
from video_straem import VideoStream
from consts import *
from camera_editor import CameraEditor
from camera_player import CamPlayer
from preset_viewer import PresetViewer


class Bzbcam(MDApp):
    dialog = None
    current_cam = None
    cam_screen = ObjectProperty()

    def __init__(self):
        super().__init__()
        self.__active_cam = dict()
        self.__index_cam: int = 0
        self.__cams = dict()
        self.__prew_point = tuple()
        self.__screenshot: np.ndarray = np.ndarray([])
        Clock.schedule_interval(self.update, 1.0 / 60)

    def on_start(self):
        cameras = session.query(Camera).all()
        for cam in cameras:
            self._add_cam_view(cam_id=cam.id,
                               name=cam.name,
                               description=cam.get_description())

    def on_stop(self):
        if self.__active_cam:
            self.__active_cam['video'].stop()
        if self.__cams:
            for _, val in self.__cams.items():
                val['video'].stop()

    def on_pause(self):
        if self.__active_cam:
            self.__active_cam['video'].pause(True)

    def on_resume(self):
        if self.root.current == "cam_player" and self.__active_cam:
            self.__active_cam['video'].pause(False)

    def update(self, dt):
        if self.__active_cam:
            frame: np.ndarray = self.__active_cam['video'].read()
            if frame.size > 1:
                # display image from the texture
                self.root.screens[CAM_PLAYER].ids.img_screen.texture = \
                    self._get_image_texture(frame)

    def _get_screenshot(self) -> np.ndarray:
        frame = np.ndarray([])
        if self.__active_cam:
            tmp = self.__active_cam['video'].read()
            if tmp.size > 1:
                frame = tmp
        return frame

    def _set_image(self, frame: np.ndarray):
        if frame.size > 1:
            self.root.screens[PRESETS_NEW].ids.img_screenshot.texture = \
                self._get_image_texture(frame)

    @staticmethod
    def _get_image_texture(frame: np.ndarray):
        if frame.size > 1:
            # convert it to texture
            buf1 = cv2.flip(frame, 0)
            image_texture = Texture.create(
                size=(frame.shape[1], frame.shape[0]), colorfmt='bgr'
            )
            image_texture.blit_buffer(
                buf1.flatten(), colorfmt='bgr', bufferfmt='ubyte'
            )
            # display image from the texture
            return image_texture

    def _add_cam_view(self, cam_id, name, description):
        cam = TwoLineAvatarIconListItem(
                text=name,
                secondary_text=description,
                id=str(cam_id)
            )
        cam.add_widget(IconLeftWidget(icon="camera-outline"))
        cam.bind(on_release=self._on_go_cam)
        self.root.screens[CAM_LIST].ids.cam_list.add_widget(cam)

    def _add_view_cam_preset(self, title, preset_id, frame: np.ndarray):
        file_name = f'{preset_id}.png'
        if not os.path.isfile(file_name):
            img = Image(self._get_image_texture(frame))
            img.save(file_name, flipped=True)
        itm = PresetViewer()
        itm.text = title
        itm.id = str(preset_id)
        itm.source = file_name
        itm.delete_preset = self._on_remove_preset
        itm.run_preset = self._on_run_preset
        self.root.screens[CAM_PLAYER].ids.preset_list.add_widget(itm)

    def _on_run_preset(self, *args):
        preset_id = int(args[0])
        preset = session.query(Preset).filter(Preset.id == preset_id).first()
        if preset:
            preset_number = preset.number
            if preset_number:
                self.__active_cam['visca'].set_preset_speed(8)
                self.__active_cam['visca'].call_preset(preset_number)

    def _on_remove_preset(self, *args):
        obj = args[1]
        preset_id = int(args[0])
        preset = session.query(Preset).filter(Preset.id == preset_id).first()
        if preset:
            session.delete(preset)
            session.commit()
            self.root.screens[CAM_PLAYER].ids.preset_list.remove_widget(obj)
            file_name = f'{preset_id}.png'
            if os.path.isfile(file_name):
                os.unlink(file_name)

    @staticmethod
    def on_menu(e):
        print("on_menu")
        print(e)

    def on_button_add_cam(self):
        self._add_cam()

    def _add_cam(self):
        self.root.transition.direction = 'left'
        self.root.current = "camera_new"
        self.root.screens[CAM_ADD].ids.toolbar.title = "Add New Camera"
        self.root.screens[CAM_ADD].cam_id = 0

    def _load_presets_from_database(self):
        self.root.screens[CAM_PLAYER].ids.preset_list.clear_widgets()
        presets = session.query(Preset).filter(
            Preset.camera_id == self.__index_cam
        ).all()
        for preset in presets:
            frame = pickle.loads(preset.img)
            self._add_view_cam_preset(
                title=preset.name,
                preset_id=preset.id,
                frame=frame
            )

    def _on_go_cam(self, e: TwoLineAvatarIconListItem):
        self.current_cam = e
        self._init_cam(int(e.id))
        self._load_presets_from_database()
        self._go_cam_player()
        self.root.screens[CAM_PLAYER].ids.toolbar2.title = f"Camera: {e.text}"

    def _go_cam_player(self):
        self.root.transition.direction = 'left'
        self.root.current = "cam_player"

    def _go_cam_player_right(self):
        self.root.transition.direction = 'right'
        self.root.current = "cam_player"

    def _go_create_preset(self):
        self.root.transition.direction = 'left'
        self.root.current = "presets_new"

    def go_cams(self):
        self.root.transition.direction = 'right'
        self.root.current = "screen_cam_list"

    def _init_cam(self, cam_id: int):
        if self.__active_cam:
            self.__active_cam['video'].pause(True)

        if self.__index_cam > 0 and self.__index_cam not in self.__cams:
            self.__cams.update({self.__index_cam: self.__active_cam})

        self.__index_cam = cam_id
        if cam_id not in self.__cams:
            camera = session.query(Camera).filter(Camera.id == cam_id).first()
            if camera:
                self.__active_cam = {
                    'visca': ViscaClient(
                        camera_ip=camera.ip_address,
                        camera_port=camera.visca_port
                    ),
                    'video': VideoStream(
                        src=rtsp_builder(
                            user_name=camera.user_name,
                            password=camera.password,
                            ip_address=camera.ip_address,
                            port=camera.rtsp_port
                        )
                    )
                }
                self.__active_cam['video'].start()
        else:
            self.__active_cam = self.__cams[cam_id]
            self.__active_cam['video'].pause(False)

    def _edit_cam(self, e: TwoLineAvatarIconListItem):
        # self.current_cam = e
        cam = session.query(Camera).filter(Camera.id == int(e.id)).first()
        if cam:
            self.root.screens[CAM_EDIT].cam_id = cam.id
            self._fill_cam_editor(
                index=1,
                title=cam.name,
                ip_address=cam.ip_address,
                visca_port=str(cam.visca_port),
                rtsp_port=str(cam.rtsp_port),
                user_name=cam.user_name,
                pwr=cam.password
            )
            self.root.transition.direction = 'left'
            self.root.current = "camera_edit"
            self.root.screens[CAM_EDIT].ids.toolbar.title = "Edit Camera"

    def _clear_cam_dlg(self, index):
        self._fill_cam_editor(index=index, title='', ip_address='', visca_port='',
                              rtsp_port='', user_name='', pwr='')

    def _fill_cam_editor(self, index: int, title: str, ip_address: str,
                         visca_port: str, rtsp_port: str,
                         user_name: str, pwr: str):
        self.root.screens[index].ids.title.text = title
        self.root.screens[index].ids.ip_address.text = ip_address
        self.root.screens[index].ids.visca_port.text = visca_port
        self.root.screens[index].ids.rtsp_port.text = rtsp_port
        self.root.screens[index].ids.user_name.text = user_name
        self.root.screens[index].ids.pwr.text = pwr

    def _cam_create(self):
        """Create new camera"""
        title = self.root.screens[CAM_ADD].ids.title.text
        ip_address = self.root.screens[CAM_ADD].ids.ip_address.text
        visca_port_tmp = self.root.screens[CAM_ADD].ids.visca_port.text
        visca_port = int(visca_port_tmp) if visca_port_tmp else 0
        rtsp_port_tmp = self.root.screens[CAM_ADD].ids.rtsp_port.text
        rtsp_port = int(rtsp_port_tmp) if rtsp_port_tmp else 0
        user_name = self.root.screens[CAM_ADD].ids.user_name.text
        password = self.root.screens[CAM_ADD].ids.pwr.text
        if title and ip_address and visca_port and rtsp_port \
                and user_name and password:
            cam = Camera()
            cam.name = title
            cam.ip_address = ip_address
            cam.visca_port = visca_port
            cam.rtsp_port = rtsp_port
            cam.user_name = user_name
            cam.password = password
            session.add(cam)
            session.commit()
            self._add_cam_view(cam.id, cam.name, cam.get_description())
        self._clear_cam_dlg(2)
        self.go_cams()

    def _save_cam(self):
        """Update camera"""
        title = self.root.screens[CAM_EDIT].ids.title.text
        ip_address = self.root.screens[CAM_EDIT].ids.ip_address.text
        visca_port_tmp = self.root.screens[CAM_EDIT].ids.visca_port.text
        visca_port = int(visca_port_tmp) if visca_port_tmp else 0
        rtsp_port_tmp = self.root.screens[CAM_EDIT].ids.rtsp_port.text
        rtsp_port = int(rtsp_port_tmp) if rtsp_port_tmp else 0
        user_name = self.root.screens[CAM_EDIT].ids.user_name.text
        password = self.root.screens[CAM_EDIT].ids.pwr.text
        if title and ip_address and visca_port and rtsp_port \
                and user_name and password:
            cam = session.query(Camera).filter(
                Camera.id == self.root.screens[CAM_EDIT].cam_id
            ).first()
            if cam:
                cam.name = title
                cam.ip_address = ip_address
                cam.visca_port = visca_port
                cam.rtsp_port = rtsp_port
                cam.user_name = user_name
                cam.password = password
                session.commit()
            self._clear_cam_dlg(CAM_EDIT)
            self.go_cams()

    def _dlg_delete_cam(self, cam_id):
        if not self.dialog:
            self.dialog = MDDialog(
                text="Delete camera?",
                size_hint_y=None,
                padding=10,
                buttons=[
                    MDFlatButton(
                        text="DELETE",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda x: self._delete_cam(cam_id)
                    ),
                    MDFlatButton(
                        text="CANCEL",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda x: self.dialog.dismiss()
                    ),
                ],
            )
        self.dialog.open()

    def _delete_cam(self, cam_id):
        self.dialog.dismiss()
        cam = session.query(Camera).filter(
            Camera.id == self.root.screens[CAM_EDIT].cam_id
        ).first()
        if cam:
            session.delete(cam)
            session.commit()
            if self.current_cam:
                self.root.screens[CAM_LIST].ids.cam_list.remove_widget(
                    self.current_cam
                )
                self.go_cams()

    def _save_preset(self):
        def find_free_cell(cam_id: int) -> int:
            cells = session.query(Preset.number).filter(
                Preset.camera_id == cam_id
            ).all()
            if cells:
                l = [itm[0] for itm in cells]
                for i in range(1, 101):
                    if i not in l:
                        return i
            return 1

        preset = Preset()
        preset.camera_id = self.__index_cam
        preset.name = self.root.screens[PRESETS_NEW].ids.title.text
        preset.speed = 7
        preset.number = find_free_cell(self.__index_cam)
        preset.img = pickle.dumps(self.__screenshot)
        session.add(preset)
        session.commit()

        self._add_view_cam_preset(title=preset.name,
                                  preset_id=preset.id,
                                  frame=self.__screenshot)

        self.__active_cam['visca'].set_preset(preset.number)

        self._go_cam_player_right()

    def _on_add_preset(self):
        self.__screenshot = self._get_screenshot()
        if self.__screenshot.size > 1:
            self._set_image(self.__screenshot)
            self._go_create_preset()

    @staticmethod
    def __calc_degrees(pos, ppos):
        xb, yb = pos
        xa, ya = ppos
        r = 0
        if xb != xa:
            tan_a = math.fabs((yb - ya) / (xb - xa))
            a = math.degrees(math.atan(tan_a))
            if xb > xa and yb > ya:
                r = a
            if xb == xa and yb > ya:
                r = 90
            if xb < xa and yb > ya:
                r = 180 - a
            if xb < xa and yb == ya:
                r = 180
            if xb < xa and yb < ya:
                r = 180 + a
            if xb == xa and yb < ya:
                r = 270
            if xb > xa and yb < ya:
                r = 360 - a
        return r

    def on_touch_down(self, args):
        obj, touch = args
        touch.grab(obj)
        self.__prew_point = touch.pos

    def on_touch_up(self, args):
        obj, touch = args
        touch.ungrab(obj)
        self.__prew_point = None
        self.__active_cam['visca'].zoom_stop()
        self.__active_cam['visca'].pan_stop()

    def on_touch_move(self, args):
        _, touch = args
        if self.__prew_point:
            degree = self.__calc_degrees(touch.pos, self.__prew_point)
            if 'multitouch_sim' in touch.profile:
                self.__active_cam['visca'].zoom_stop()
                if 270 >= degree > 90:
                    self.__active_cam['visca'].zoom_tele()
                else:
                    self.__active_cam['visca'].zoom_wide()
            else:
                # print(degree)
                self.__active_cam['visca'].pan_stop()
                if 135 >= degree > 45:
                    self.__active_cam['visca'].pan_up()
                elif 225 >= degree > 135:
                    self.__active_cam['visca'].pan_left()
                elif 315 >= degree > 225:
                    self.__active_cam['visca'].pan_down()
                else:
                    self.__active_cam['visca'].pan_right()
