import cv2
import time

# URL RTSP récupérée depuis ONVIF (via GetStreamUri par ex.)
ip_camera = "192.168.0.179"
rtsp_url = f"rtsp://admin:1234567890@{ip_camera}:554/channel=0_stream=1&onvif=0.sdp?real_stream="

# Ouvre le flux vidéo
cap = cv2.VideoCapture(rtsp_url)
# Variables for FPS calculation


if not cap.isOpened():
    print("❌ Impossible d'ouvrir le flux vidéo")
else:
    print("✅ Connexion réussie")
    frame_count = 0
    start_time = time.time()
    # Get the actual resolution
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Or use 'MJPG'
    out = cv2.VideoWriter('/tmp/output.avi', fourcc, 20.0, (width, height))


    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Échec de lecture de frame")
            break

        frame_count += 1
        elapsed_time = time.time() - start_time
        out.write(frame)  # Save frame to video

        if elapsed_time > 0:
            fps = frame_count / elapsed_time
            print(f"FPS: {fps:.2f}", end="\r")

        # Touche 'q' pour quitter
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
