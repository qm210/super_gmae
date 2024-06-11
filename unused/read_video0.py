import cv2
print("CV2 version", cv2.__version__)


def be_an_awesome_fucker():
    # Open the video stream from the HDMI-USB adapter
    cap = cv2.VideoCapture('/dev/video0')

    while True:
        # Read a frame from the video stream
        ret, frame = cap.read()

        if not ret:
            break

        # Display the frame in a window
        cv2.imshow('Incoming Picture', frame)

        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video stream and close all windows
    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    be_an_awesome_fucker()
