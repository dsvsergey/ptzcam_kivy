import os
from threading import Thread, Lock
import cv2
import numpy as np
from dotenv import load_dotenv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR.parent / ".env"
load_dotenv(env_path)


class VideoStream:
    def __init__(self, src, width=320, height=240):
        self.thread = Thread(target=self.update, args=())
        self._src = src
        self._is_connect = False
        # self.stream = cv2.VideoCapture()
        # self.stream.open(src)
        # self.stream.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, width)
        # self.stream.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, height)
        # (self.grabbed, self.frame) = self.stream.read()
        self.grabbed, self.frame = None, np.ndarray([])
        self.started = False
        self._pause = False
        self.read_lock = Lock()

    def start(self):
        if self.started:
            return None
        self.started = True
        self.thread.start()
        return self

    def update(self):
        stream = cv2.VideoCapture()
        self.read_lock.acquire()
        stream.open(self._src)
        self._is_connect = True
        self.read_lock.release()
        while self.started:
            if not self._pause:
                (grabbed, frame) = stream.read()
                self.read_lock.acquire()
                self.grabbed, self.frame = grabbed, frame
                self.read_lock.release()
        stream.release()

    def read(self) -> np.ndarray:
        frame = np.ndarray([])
        if not self._is_connect:
            return frame
        self.read_lock.acquire()
        if self.grabbed:
            frame = self.frame.copy()
        self.read_lock.release()
        return frame

    def stop(self):
        self.started = False
        self.thread.join()

    def pause(self, val):
        self._pause = val
        # self.thread.join()


if __name__ == "__main__":
    vs = VideoStream(src=os.getenv("SRC")).start()
    while True:
        frame = vs.read()
        if frame.any():
            cv2.imshow("webcam", frame)
        if cv2.waitKey(1) == 27:
            break

    vs.stop()
    cv2.destroyAllWindows()
