import cv2
import numpy as np
import pyautogui
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import mediapipe as mp
import math
import screen_brightness_control as sbc


class HandTracker:

    def __init__(self, static_image_mode=False, model_complexity=1, min_detection_confidence=0.5,
                 min_tracking_confidence=0.5, max_num_hands=2, FRAME_WIDTH=640, FRAME_HEIGHT=480):
        self.static_image_mode = static_image_mode
        self.model_complexity = model_complexity
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.max_num_hands = max_num_hands
        self.devices = AudioUtilities.GetSpeakers()
        self.interface = self.devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.volume = cast(self.interface, POINTER(IAudioEndpointVolume))
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands()
        self.mp_draw = mp.solutions.drawing_utils
        self.SCREEN_WIDTH, self.SCREEN_HEIGHT = pyautogui.size()
        self.FRAME_WIDTH, self.FRAME_HEIGHT = FRAME_WIDTH, FRAME_HEIGHT
        self.scale = 1
        self.mute_status = False

    def track_hands(self, frame, hand_lm):

        # initialize with max and min float values
        x_min, y_min, x_max, y_max = float('inf'), float('inf'), float('-inf'), float('-inf')

        # locate the min and max landmark pos.
        for landmark in hand_lm.landmark:
            x = int(landmark.x * self.FRAME_WIDTH)
            y = int(landmark.y * self.FRAME_HEIGHT)
            x_min = min(x_min, x)
            y_min = min(y_min, y)
            x_max = max(x_max, x)
            y_max = max(y_max, y)
            cv2.circle(frame, (x, y), 7, (255, 0, 255), cv2.FILLED)

        # draw bounding box
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

        return frame

    def draw_hand_landmarks(self, frame, hand_lm):
        self.mp_draw.draw_landmarks(frame,
                                    hand_lm,
                                    self.mp_hands.HAND_CONNECTIONS,
                                    landmark_drawing_spec=self.mp_draw.DrawingSpec((0, 0, 255), 3, 2),
                                    connection_drawing_spec=self.mp_draw.DrawingSpec((0, 255, 0), 3, 2)
                                    )
        return frame

    def get_landmarks(self, hand_lm, landmarks_list):
        for landmarks in hand_lm.landmark:
            x, y = int(landmarks.x * self.FRAME_WIDTH), int(landmarks.y * self.FRAME_HEIGHT)
            landmarks_list.append([x, y])
        return landmarks_list

    def finger_check(self, hand_lm, landmarks_list, handedness):

        # Storing statuses for each finger
        finger_status = [0] * 5

        # Storing indices for each fingertip
        finger_tips_inds = [self.mp_hands.HandLandmark.INDEX_FINGER_TIP,
                            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
                            self.mp_hands.HandLandmark.RING_FINGER_TIP, self.mp_hands.HandLandmark.PINKY_TIP]

        for _id, tip_ids in enumerate(finger_tips_inds):
            if hand_lm.landmark[tip_ids].y < hand_lm.landmark[tip_ids - 2].y:
                finger_status[_id + 1] = 1
            else:
                finger_status[_id + 1] = 0

        thumb_tip = landmarks_list[4]
        thumb_mcp = landmarks_list[2]

        if (handedness == 'Right' and (thumb_tip[0] < thumb_mcp[0])) or (
                handedness == 'Left' and (thumb_tip[0] > thumb_mcp[0])):
            finger_status[0] = 1
        else:
            finger_status[0] = 0

        return finger_status

    def cursor(self, frame, landmarks_list):
        cursor_x = int(landmarks_list[8][0] / self.FRAME_WIDTH * self.SCREEN_WIDTH * self.scale)
        cursor_y = int(landmarks_list[8][1] / self.FRAME_HEIGHT * self.SCREEN_HEIGHT * self.scale)
        pyautogui.moveTo(cursor_x, cursor_y, duration=0.1, _pause=False)

    def click(self, landmarks_list):
        if landmarks_list[12][1] >= landmarks_list[10][1]:
            pyautogui.click()

    def set_volume_status(self, finger_status):

        # Volume Mute / Unmute
        if finger_status[1] and finger_status[4] and not finger_status[0] and not finger_status[2]:
            self.volume.SetMute(1, None)
            self.mute_status = True

        elif finger_status[0] == 1 and finger_status[4] == 1 and finger_status[1] == 0 and \
                finger_status[2] == 0 and self.mute_status:
            self.volume.SetMute(0, None)
            self.mute_status = False

    def set_volume_range(self, frame, finger_status, landmarks_list):
        # Raise/ Lower Volume

        if finger_status[0] and finger_status[1] and not finger_status[2] and not finger_status[3] and not finger_status[4]:
            x_1, y_1 = landmarks_list[4][0], landmarks_list[4][1]
            x_2, y_2 = landmarks_list[8][0], landmarks_list[8][1]

            cv2.line(frame, (x_1, y_1), (x_2, y_2), (0, 255, 255), 3)

            dist = int(math.hypot(x_2 - x_1, y_2 - y_1))

            volumePercent = int(np.interp(dist, [30, 110], [0, 100]))
            volumeBar = int(np.interp(dist, [30, 110], [400, 150]))

            # Create a Level Bar for Volume
            cv2.putText(frame, f"Volume Level : {volumePercent} %", (self.FRAME_WIDTH - 300, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.rectangle(frame, (self.FRAME_WIDTH - 50, 150), (self.FRAME_WIDTH - 80, 400), (255, 255, 0),
                          3)

            if volumePercent < 49:
                cv2.rectangle(frame, (self.FRAME_WIDTH - 50, volumeBar), (self.FRAME_WIDTH - 80, 400), (0, 255, 0),
                              cv2.FILLED)

            elif 49 < volumePercent < 89:
                cv2.rectangle(frame, (self.FRAME_WIDTH - 50, volumeBar), (self.FRAME_WIDTH - 80, 400), (0, 255, 255),
                              cv2.FILLED)

            elif volumePercent > 89:
                cv2.rectangle(frame, (self.FRAME_WIDTH - 50, volumeBar), (self.FRAME_WIDTH - 80, 400), (0, 0, 255),
                              cv2.FILLED)

            # print(volumePercent)

            cv2.circle(frame, (x_2, y_2), 7, (255, 0, 255), cv2.FILLED)
            cv2.circle(frame, (x_1, y_1), 7, (255, 0, 255), cv2.FILLED)
            self.volume.SetMasterVolumeLevelScalar(volumePercent / 100, None)
        return frame

    def set_brightness(self, frame, finger_status, landmarks_list):
        # Raise/ Lower Brightness
        if finger_status[0] and finger_status[2] and not finger_status[1] and not finger_status[3] and not finger_status[4]:
            x_1, y_1 = landmarks_list[4][0], landmarks_list[4][1]
            x_2, y_2 = landmarks_list[12][0], landmarks_list[12][1]

            cv2.line(frame, (x_1, y_1), (x_2, y_2), (0, 255, 255), 3)

            dist = int(math.hypot(x_2 - x_1, y_2 - y_1))

            brightness_level = int(np.interp(dist, [30, 110], [0, 100]))
            brightnessBar = int(np.interp(dist, [30, 110], [400, 150]))

            # Create a Level Bar for Brightness
            cv2.putText(frame, f"Brightness Level : {brightness_level} %", (self.FRAME_WIDTH - 300, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.rectangle(frame, (self.FRAME_WIDTH - 50, 150), (self.FRAME_WIDTH - 80, 400), (255, 255, 0),
                          3)

            if brightness_level < 49:
                cv2.rectangle(frame, (self.FRAME_WIDTH - 50, brightnessBar), (self.FRAME_WIDTH - 80, 400), (0, 255, 0),
                              cv2.FILLED)

            elif 49 < brightness_level < 89:
                cv2.rectangle(frame, (self.FRAME_WIDTH - 50, brightnessBar), (self.FRAME_WIDTH - 80, 400),
                              (0, 255, 255),
                              cv2.FILLED)

            elif brightness_level > 89:
                cv2.rectangle(frame, (self.FRAME_WIDTH - 50, brightnessBar), (self.FRAME_WIDTH - 80, 400), (0, 0, 255),
                              cv2.FILLED)

            cv2.circle(frame, (x_2, y_2), 7, (255, 0, 255), cv2.FILLED)
            cv2.circle(frame, (x_1, y_1), 7, (255, 0, 255), cv2.FILLED)

            sbc.set_brightness(brightness_level)
        return frame
