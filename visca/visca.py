import socket
import binascii  # for printing the messages we send, not really necessary
from time import sleep

import visca.protocols as vp
# import protocols as vp


class ViscaClient:
    def __init__(self, camera_ip, camera_port):
        self._camera_ip = camera_ip
        self._camera_port = camera_port
        self._soket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4, UDP
        self._buffer_size = 1024
        self._sequence_number = 0

    def _memory_recall_function(self, memory_number):
        message_string = vp.memory_recall.replace('p', str(memory_number))
        self._send_message(vp.information_display_off)  # otherwise we see a message on the camera output
        sleep(0.25)
        message = self._send_message(message_string)
        sleep(1)
        self._send_message(vp.information_display_off)
        return message

    def _memory_set_function(self, memory_number):
        message_string = vp.memory_set.replace('p', str(memory_number))
        message = self._send_message(message_string)
        return message

    def _send_message(self, message_string):
        r = False
        try:
            payload_type = bytearray.fromhex('01 00')
            payload = bytearray.fromhex(message_string)
            payload_length = len(payload).to_bytes(2, 'big')
            message = payload_type + payload_length + self._sequence_number.to_bytes(4, 'big') + payload
            self._sequence_number += 1
            self._soket.sendto(message, (self._camera_ip, self._camera_port))
            r = True
        except socket.error:
            pass
        finally:
            return r

    def _send_message_with_feedback(self, message_string):
        try:
            message = bytearray.fromhex(message_string)
            self._soket.sendto(message, (self._camera_ip, self._camera_port))
            self._soket.settimeout(0.4)
            answer = self._soket.recvfrom(1024)
            data, _ = answer
            data = binascii.hexlify(data)
            return data
        except socket.error:
            return None

    def _reset_sequence_number_function(self):
        try:
            reset_sequence_number_message = bytearray.fromhex('02 00 00 01 00 00 00 01 01')
            self._soket.sendto(reset_sequence_number_message, (self._camera_ip,
                                                               self._camera_port))
            self._sequence_number = 1
            return self._sequence_number
        except socket.error:
            return None

    def connect(self):
        self._reset_sequence_number_function()

    def camera_on(self):
        self._send_message(vp.camera_on)

    def get_info(self):
        return self._camera_ip, self._camera_port

    def pan_up(self):
        command = vp.pan_up()
        self._send_message(command)

    def pan_left(self):
        command = vp.pan_left()
        self._send_message(command)

    def pan_right(self):
        command = vp.pan_right()
        self._send_message(command)

    def pan_down(self):
        command = vp.pan_down()
        self._send_message(command)

    def pan_up_left(self):
        command = vp.pan_up_left()
        self._send_message(command)

    def pan_up_right(self):
        command = vp.pan_up_right()
        self._send_message(command)

    def pan_down_left(self):
        command = vp.pan_down_left()
        self._send_message(command)

    def pan_down_right(self):
        command = vp.pan_down_right()
        self._send_message(command)

    def pan_stop(self):
        self._send_message(vp.pan_stop())

    def pan_home(self):
        self._send_message(vp.pan_home)

    def zoom_tele(self):
        """Zoom In"""
        self._send_message(vp.zoom_tele)

    def zoom_stop(self):
        """Zoom Stop"""
        self._send_message(vp.zoom_stop)

    def zoom_wide(self):
        """Zoom Out"""
        self._send_message(vp.zoom_wide)

    def focus_near(self):
        """Focus Near"""
        self._send_message(vp.focus_near)

    def focus_far(self):
        """Focus Far"""
        self._send_message(vp.focus_far)

    def information_display_off(self):
        """Info Off"""
        self._send_message(vp.information_display_off)

    @staticmethod
    def set_speed(val):
        vp.movement_speed = '{:02}'.format(val)
        vp.pan_speed = vp.movement_speed
        vp.tilt_speed = vp.movement_speed

    @staticmethod
    def get_speed():
        return vp.movement_speed

    def call_preset(self, mem_no: int):
        self._memory_recall_function(mem_no)

    def set_preset(self, mem_no: int):
        self._memory_set_function(mem_no)

    def i2v(self, value):
        """
        return word as dword in visca format
        packets are not allowed to be 0xff
        so for numbers the first nibble is 0000
        and 0xfd gets encoded into 0x0f 0x0xd
        """
        if type(value) == str:
            value = int(value)
        ms = (value & 0b1111111100000000) >> 8
        ls = (value & 0b0000000011111111)
        p = (ms & 0b11110000) >> 4
        r = (ls & 0b11110000) >> 4
        q = ms & 0b1111
        s = ls & 0b1111
        return chr(p) + chr(q) + chr(r) + chr(s)

    def set_preset_speed(self, new_val: int):
        command = vp.set_preset_speed(new_val)
        self._send_message(command)

    def get_preset_speed(self) -> int:
        command = vp.get_preset_speed
        ans = self._send_message_with_feedback(command)
        r = int(ans[-4:-2]) if ans else 0
        return r


if __name__ == "__main__":
    vc = ViscaClient(camera_ip="192.168.20.183", camera_port=1259)
    vc.set_preset_speed(6)
    val = vc.get_preset_speed()
    print(val)
