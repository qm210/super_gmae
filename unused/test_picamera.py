import time
import picamera2
import cv2
import numpy as np

"""
This was my attempt for the Raspberry Pi. Ignore for now.

Does not work real-time, but records a file with picamera2 and displays that with cv2
"""

with picamera2.PiCamera() as camera:
    camera.start_preview()
    camera.resolution = (1920, 1080)
    camera.start_recording('output.h264', format='h264')
    time.sleep(10)
    camera.stop_recording()

cap = cv2.VideoCapture('output.h264')
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow('Video', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
