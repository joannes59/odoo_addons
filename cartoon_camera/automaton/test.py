import cv2
import time

# Open the USB camera (0 is usually the default camera)
camera = cv2.VideoCapture(0)

# Check if the camera is opened correctly
if not camera.isOpened():
    raise RuntimeError("Cannot open the USB camera")

# Set the resolution if needed
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Get the actual resolution
width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Or use 'MJPG'
out = cv2.VideoWriter('/tmp/output.avi', fourcc, 20.0, (width, height))

# Variables for FPS calculation
frame_count = 0
start_time = time.time()

print("Recording... Press 'q' to quit")

while True:
    ret, frame = camera.read()
    if not ret:
        print("Failed to grab frame")
        break

    #out.write(frame)  # Save frame to video
    cv2.imshow('Camera', frame)  # Show the frame in a window

    frame_count += 1
    elapsed_time = time.time() - start_time

    if elapsed_time > 0:
        fps = frame_count / elapsed_time
        print(f"FPS: {fps:.2f}", end="\r")

    # Press 'q' to stop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release everything
camera.release()
out.release()
cv2.destroyAllWindows()

# Final FPS report
total_time = time.time() - start_time
final_fps = frame_count / total_time
print(f"\nFinal FPS: {final_fps:.2f}")
