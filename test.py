import cv2
from HandTracker import HandTracker


def capture_video(source):
    # Set Video Capture Source
    cap = cv2.VideoCapture(source)

    # Load the tracker
    hand_tracker = HandTracker()

    try:
        while cap.isOpened():

            _, frame = cap.read()

            # Resizing frames based on user need
            frame = cv2.resize(frame, (hand_tracker.FRAME_WIDTH, hand_tracker.FRAME_HEIGHT))

            # Flipping the frame to opposite side
            frame = cv2.flip(frame, 1)

            frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            Process = hand_tracker.hands.process(frameRGB)

            landmarks_list = []

            if Process.multi_hand_landmarks:  # Check if one or more than hands are present
                for hand_lm in Process.multi_hand_landmarks:

                    handedness = Process.multi_handedness[Process.multi_hand_landmarks.index(hand_lm)].classification[
                        0].label

                    frame = hand_tracker.track_hands(frame, hand_lm)  # Tracks the hand position

                    frame = hand_tracker.draw_hand_landmarks(frame, hand_lm)  # Tracks every joint of hand

                    landmarks_list = hand_tracker.get_landmarks(hand_lm,
                                                                landmarks_list)  # store landmarks of each finger

                    finger_status = hand_tracker.finger_check(hand_lm, landmarks_list,
                                                              handedness)  # store the status of each extended (Fingers standing up) fingers

                    if handedness == "Right":

                        # Cursor gesture
                        hand_tracker.cursor(frame, landmarks_list)
                        # Click gesture
                        hand_tracker.click(landmarks_list)

                    elif handedness == "Left":

                        # Changes the volume status
                        hand_tracker.set_volume_status(finger_status)

                        # Turns the volume up/down
                        frame = hand_tracker.set_volume_range(frame, finger_status, landmarks_list)

                        # Changes screen brightness
                        frame = hand_tracker.set_brightness(frame, finger_status, landmarks_list)

            cv2.imshow('Video', frame)  # displays each frame

            if cv2.waitKey(1) and 0xFF == ' ':
                break
    except Exception as e:
        print("Error: ", e)

    cap.release()


if __name__ == "__main__":
    capture_video(0)
