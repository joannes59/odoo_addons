from ultralytics import YOLO
import cv2
from bytetrack import BYTETracker
import numpy as np
import json

# 📺 RTSP or USB camera
ip_camera = "192.168.0.179"
CAMERA_URL = f"rtsp://admin:1234567890@{ip_camera}:554/channel=0_stream=1&onvif=0.sdp?real_stream="
# CAMERA_URL = 0  # use 0 for USB webcam

# 📦 Load YOLOv8 model (person detection)
model = YOLO("yolov8n.pt")  # 'n' for nano (fast), or 's'/'m' if GPU

# 🏃 Setup tracker (ByteTrack)
tracker = BYTETracker()

# 📖 Store tracked positions
tracked_positions = []

# 🎥 Open video stream
cap = cv2.VideoCapture(CAMERA_URL)
if not cap.isOpened():
    print("❌ Cannot open camera")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 👁️ YOLO inference
    results = model.predict(frame, verbose=False)[0]

    # 📋 Extract person detections (class id 0 in COCO)
    detections = []
    for box in results.boxes:
        if int(box.cls[0]) == 0:  # only 'person'
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            detections.append([x1, y1, x2, y2, conf])

    # 🏃 Update tracker
    tracks = tracker.update(np.array(detections), frame.shape)

    # 🎯 Draw tracked boxes and IDs
    for track in tracks:
        x1, y1, x2, y2, track_id = track.tlwh[0], track.tlwh[1], track.tlwh[0]+track.tlwh[2], track.tlwh[1]+track.tlwh[3], track.track_id
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"ID {track_id}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 📝 Save positions
        tracked_positions.append({
            "id": int(track_id),
            "bbox": (x1, y1, x2 - x1, y2 - y1)
        })

    # 🖥️ Show result
    cv2.imshow("YOLOv8 + ByteTrack", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 📝 Save positions to file
with open("tracked_positions.json", "w") as f:
    json.dump(tracked_positions, f, indent=2)

# Cleanup
cap.release()
cv2.destroyAllWindows()
