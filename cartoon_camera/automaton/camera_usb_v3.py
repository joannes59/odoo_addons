import cv2
import time
from ultralytics import YOLO
import urllib.request
import numpy as np
import time
import json
import httpx
import multiprocessing
import torch
from boxmot import BoostTrack
from boxmot import ByteTrack
from boxmot import OcSort
from pathlib import Path
import threading
import argparse
from collections import Counter
import math
import os
import datetime
import tracking

red_color = (0, 0, 255)
green_color = (0, 255, 0)
blue_color = (255, 0, 0)
KEYPOINTS_FACE = [0, 1, 2, 3, 4]

class CameraDetection:
    def __init__(self):
        self.camera_usb_number = None
        self.camera = None
        self.camera_width = 800
        self.camera_height = 600
        self.camera_fps = []
        self.camera_frame = None
        self.camera_frame_previews = None
        self.frame = None

        # resolution: 1280 800 FPS: 11
        # resolution: 800 600 FPS: 20
        # resolution: 640 480: FPS: 33
        # resolution: 320 240 FPS: 200

        # Réglages possibles (valeurs à adapter à ta caméra)
        # cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)   # Luminosité (0.0 à 1.0 ou plage spécifique)
        # cap.set(cv2.CAP_PROP_CONTRAST, 0.5)     # Contraste
        # cap.set(cv2.CAP_PROP_SATURATION, 0.5)   # Saturation
        # cap.set(cv2.CAP_PROP_HUE, 0.5)          # Teinte
        # cap.set(cv2.CAP_PROP_SHARPNESS, 0.5)    # Netteté (pas toujours pris en charge)
        # cap.set(cv2.CAP_PROP_GAMMA, 0.5)        # Gamma
        # cap.set(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, 4500)  # Balance des blancs (Kelvin)
        # cap.set(cv2.CAP_PROP_BACKLIGHT, 1)      # Compensation du rétroéclairage
        # cap.set(cv2.CAP_PROP_EXPOSURE, -4)      # Exposition (souvent négatif = automatique désactivé)

        self.grid_origin = (int(0.2 * self.camera_width), int(0.45 * self.camera_height))
        self.grid_dimension = 5
        self.grid_max_value = 1000

        self.grid = []
        self.grid_pt_selected = (0, 0)

        self.yolo_model_name = "yolo11n-pose.pt"
        self.yolo_conf = 0.5 # seuil de confiance
        self.yolo_filter_class = [0] # 0: personne, list of class to track
        self.yolo_model = None
        self.tracker = cv2.legacy.TrackerCSRT_create()
        self.boosttrack = None
        self.bytetrack = None
        self.ocsort = None
        self.tracker_fields = ['track_id'] # , 'track_boost_id', 'track_byte_id', 'track_ocsort_id']
        self.zone_detection = []
        self.box_detection = []
        self.tracking_detection = []
        self.tracking_seuil = 0.25 # surface minimum to link a lost box detection
        self.lost_frame_max = 60

        self.lost_distance = 0.25 * self.grid_max_value
        self.tracking_index = 0
        self.last_position_max = 5
        self.sending_url = 'http://localhost:8000/camera/detection'

        self.stat_ok = [0,] * len(self.tracker_fields)
        self.stat_lost = [0,] * len(self.tracker_fields)
        self.stat_new = [0,] * len(self.tracker_fields)

        self.stat_ok_count = 0
        self.stat_last_count = 0
        self.stat_new_count = 0
        self.out_file_path = ''
        self.out_time = 0

        self.time_start = None
        self.time_mean = []
        self.time_fps = ''

        self.key_plot = 0
        self.key_action = ''

        self.lock = threading.Lock()
        self.running = False
        self.thread = None

        self.surface_mini = 0.1



    def update(self):
        while self.running:
            if self.camera is not None:
                ret, frame = self.camera.read()
                if ret:
                    with self.lock:
                        self.frame = frame
                        self.camera_fps.append(time.time())
                        if len(self.camera_fps) > 10:
                            del(self.camera_fps[0])
            time.sleep(0.001)

    def detect_camera(self):
        """ detect camera if needed, put USB number"""
        camera_usb_number = 0
        cap = cv2.VideoCapture(camera_usb_number)
        while not cap.isOpened():
            camera_usb_number += 1
            cap = cv2.VideoCapture(camera_usb_number)
            if camera_usb_number > 8:
                self.camera_usb_number = None
                break
        cap.release()
        self.camera_usb_number = camera_usb_number

    def init_camera(self):
        """ open camera """
        if self.camera_usb_number is None:
            self.detect_camera()

        self.camera = cv2.VideoCapture(self.camera_usb_number)
        # (640, 480), 960x720 (1280, 800), (1920, 1080), (2560, 1440), (960, 720), (800, 600), (960, 720),

        resolutions = [(800, 600), (960, 720), (960, 540), (640, 480), (1280, 720)]
        for (w, h) in resolutions:
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            rw = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            rh = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if (rw, rh) == (w, h):
                self.camera_width = w
                self.camera_height = h
                break

        self.thread = threading.Thread(target=self.update, daemon=True)
        self.running = True
        self.thread.start()
        time.sleep(0.5)

    def get_camera_frame(self):

        if self.camera_frame is not None:
            self.camera_frame_previews = self.camera_frame.copy()

        if self.running:
            # input camera
            with self.lock:
                frame = self.frame.copy() if self.frame is not None else None
        elif self.camera is not None:
            # input video
            ret, frame = self.camera.read()
            if not ret:
                frame = None
        else:
            frame = None

        self.camera_frame = frame
        if frame is not None and self.camera_frame_previews is None:
            self.camera_frame_previews = frame

    def stop_camera(self):
        if self.running:
            self.running = False
            self.thread.join()
        self.camera.release()


    def save_to_json(self, filepath="config.json"):
        """ Save config to file """
        data = {
            "camera_width": self.camera_width,
            "camera_height": self.camera_height,
            "grid": self.grid,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load_from_json(self, filepath="config.json"):
        """Chargement des attributs depuis un fichier JSON"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

    def track_fps(self, nb_time=10):
        """ track FPS """
        time_start = time.time()
        camera_fps = self.camera_fps
        if camera_fps:
            camera_time = (camera_fps[-1] - camera_fps[0]) / len(camera_fps)
        else:
            camera_time = 1.0

        if self.time_start is not None:
            time_mean = time_start - self.time_start
            self.time_mean.append(time_mean)
            self.time_fps = "1"

        if len(self.time_mean) > nb_time:
            del(self.time_mean[0])
            pose_time =  sum(self.time_mean) / len(self.time_mean)
            fps = int(1.0 / pose_time)
            self.time_fps = f"{int(fps)}: Cam: {int(100 * camera_time)} ms, Pos: {int(100 * pose_time)} ms"
        self.time_start = time_start

    def init_video(self, video_path=None):
        """ Ouvre un fichier vidéo pour test """

        self.camera = cv2.VideoCapture(video_path)
        # Vérifier si l'ouverture a réussi
        if not self.camera.isOpened():
            raise ValueError("Impossible d'ouvrir la source vidéo")
        self.camera_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.camera_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def end_camera(self):
        """ resource free """
        self.camera.release()

    def init_model(self):
        """ Load a yolo model and tracker """
        # Set device
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.yolo_model = YOLO(self.yolo_model_name)
        self.yolo_model.to(device)
        # Initialize tracker
        """
        Initializes the BoostTrack tracker with various parameters.

        Args:
            reid_weights: Path to the re-identification model weights.
            device: Device to run the model on (e.g., 'cpu', 'cuda').
            half: Whether to use half-precision for computations.
            max_age: 60, Maximum allowed frames without update.
            min_hits: 3, Minimum hits required to output a track.
            det_thresh: 0.6, Detection confidence threshold.
            iou_threshold: 0.3, IoU threshold for association.
            use_ecc: Whether to use ECC for camera motion compensation.
            min_box_area: 10, Minimum box area for detections.
            aspect_ratio_thresh: Aspect ratio threshold for detections.
            cmc_method: Method for camera motion compensation.
            lambda_iou: 0.5 Weight for IoU-based association.
            lambda_mhd: 0.25 Weight for Mahalanobis distance-based association.
            lambda_shape: 0.25 Weight for shape-based association.
            use_dlo_boost: true Whether to use DLO boost.
            use_duo_boost: true Whether to use DUO boost.
            dlo_boost_coef: 0.65 Coefficient for DLO boost.
            s_sim_corr: Whether to use shape similarity correction.
            use_rich_s: Whether to use rich shape features.
            use_sb: false Whether to use soft-BIoU.
            use_vt: false Whether to use visual tracking.
            with_reid: Whether to use re-identification.
            per_class: If True, enables per-class tracking, where tracks are managed separately for each class.
        """
        self.boosttrack = BoostTrack(
            reid_weights=Path('osnet_x0_25_msmt17.pt'),  # chemin vers ton modèle ReID
            det_thresh=0.5,
            min_hits=1,
            max_age=20,
            device=device,
            half=torch.cuda.is_available()  # utilise half precision si tu veux (True pour GPU)
        )
        """
        BYTETracker: A tracking algorithm based on ByteTrack, which utilizes motion-based tracking.

        Args:
            min_conf (float, optional): 0.1 Threshold for detection confidence. Detections below this threshold are discarded.
            track_thresh (float, optional): 0.45 Threshold for detection confidence. Detections above this threshold are considered for tracking in the first association round.
            match_thresh (float, optional): 0.8 Threshold for the matching step in data association. Controls the maximum distance allowed between tracklets and detections for a match.
            track_buffer (int, optional): 25 Number of frames to keep a track alive after it was last detected. A longer buffer allows for more robust tracking but may increase identity switches.
            frame_rate (int, optional): 30 Frame rate of the video being processed. Used to scale the track buffer size.
            per_class (bool, optional): Whether to perform per-class tracking. If True, tracks are maintained separately for each object class.
        """
        self.bytetrack = ByteTrack(
            match_thresh=0.8, # plus eleve plus permissif
            track_thresh=0.45,
            track_buffer=20,
            frame_rate=10,  # adapte selon ta vidéo
        )
        """
        OCSort Tracker: A tracking algorithm that utilizes motion-based tracking.

        Args:
            per_class (bool, optional): Whether to perform per-class tracking. If True, tracks are maintained separately for each object class.
            det_thresh (float, optional): Detection confidence threshold. Detections below this threshold are ignored in the first association step.
            max_age (int, optional): 30 Maximum number of frames to keep a track alive without any detections.
            min_hits (int, optional): 3 Minimum number of hits required to confirm a track.
            asso_threshold (float, optional): 0.3 Threshold for the association step in data association. Controls the maximum distance allowed between tracklets and detections for a match.
            delta_t (int, optional): 3 Time delta for velocity estimation in Kalman Filter.
            asso_func (str, optional): Association function to use for data association. Options include "iou" for IoU-based association.
            inertia (float, optional): 0.2 Weight for inertia in motion modeling. Higher values make tracks less responsive to changes.
            use_byte (bool, optional): false Whether to use BYTE association in the second association step.
            Q_xy_scaling (float, optional): 0.01 Scaling factor for the process noise covariance in the Kalman Filter for position coordinates.
            Q_s_scaling (float, optional): 0.0001 Scaling factor for the process noise covariance in the Kalman Filter for scale coordinates.
        """
        self.ocsort = OcSort(
            det_thresh=0.25,
            max_age=20,
            inertia=0.3,
            min_hits=1,
        )

    def get_yolo_tracking(self):
        """ return yolo tracking """
        box_detection = []

        frame = self.camera_frame.copy()

        if frame is not None:

            results = self.yolo_model.track(frame,
                                            tracker="custom_tracker.yaml",
                                            classes=self.yolo_filter_class,
                                            conf=self.yolo_conf,
                                            imgsz=self.camera_width,
                                            persist=True)
            detections = results[0].boxes.xyxy  # Coordonnées [x1, y1, x2, y2]
            classes = results[0].boxes.cls  # Indices des classes détectées
            confs = results[0].boxes.conf  # Niveaux de confiance
            track_ids = results[0].boxes.id
            keypoints_ids = results[0].keypoints.xy if results[0].keypoints is not None else []

            # sauvegarder les boîtes detectées
            for i, box in enumerate(detections):

                class_id = int(classes[i])
                x1, y1, x2, y2 = map(int, box)  # Conversion en int
                conf = float(confs[i])
                keypoints =  keypoints_ids[i].tolist()

                if track_ids is not None:
                    track_id = int(track_ids[i])
                else:
                    track_id = 0

                label = f"{track_id} - {class_id} {conf:.2f}"
                new_track = tracking.BoxDetection(x1, y1, x2, y2, label, conf, class_id, track_id)
                if keypoints:
                    new_track.keypoints = keypoints
                box_detection.append(new_track)

        self.box_detection = box_detection

    def show_tracking(self, frame):
        """ Add yolo box detection on frame """
        frame_init = frame.copy()
        label_fps = f'{frame.shape} FPS: {self.time_fps}'
        cv2.putText(frame, label_fps, (10, 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.putText(frame, f'ok   : {self.stat_ok}', (10, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(frame, f'lost  : {self.stat_lost}', (10, 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(frame, f'new  : {self.stat_new}', (10, 61),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        for bd in self.tracking_detection:
            label = f'{bd.tracking_id}: {bd.track_id}.{bd.state}'
            color = green_color
            if bd.state == 'lost':
                label += f':{bd.lost_frame}'
                color = blue_color
            elif bd.state == 'new':
                color = red_color

            label += f'-{int(100.0 * bd.conf)}%'
            cv2.rectangle(frame, (bd.x1, bd.y1), (bd.x2, bd.y2), color, 2)
            cv2.putText(frame, label, (bd.x1, bd.y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            cv2.putText(frame, f' {bd.tracking_ok}', (bd.x1, bd.y1 + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, green_color, 2)
            cv2.putText(frame, f' {bd.tracking_ko}', (bd.x1, bd.y1 + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, blue_color, 2)

            # Dessine les keypoints
            if bd.keypoints:
                x_vals = []
                y_vals = []
                for idx in KEYPOINTS_FACE:
                    (px, py) = bd.keypoints[idx]
                    x_vals.append(int(px))
                    y_vals.append(int(py))

                    cv2.circle(frame, (int(px), int(py)), 3, (0, 0, 255), 2)

                bd.get_facing()
                gender = bd.get_gender(frame_init)
                cv2.rectangle(frame, (bd.face_x1, bd.face_y1), (bd.face_x2, bd.face_y2), green_color, 2)
                cv2.putText(frame, f' {bd.facing} - {bd.gender}', (bd.face_x1, bd.face_y2 + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, green_color, 1)



        # Show no tracking box
        for bd_void in self.box_detection:
            if bd_void.state == "tracking" and not bd_void.track_id:
                cv2.rectangle(frame, (bd_void.x1 -1, bd_void.y1 -1), (bd_void.x2 +1, bd_void.y2 + 1), (0,0,0), 2)

        return frame

    def key_press(self, key):
        """ change box zone detection """

        if key == 32:
            # space press
            pass

        else:
            x = 0
            y = 0
            delta = 5
            if key == 82:  # flèche haut
                y -= delta
            elif key == 84:  # flèche bas
                y += delta
            elif key == 81:  # flèche gauche
                x -= delta
            elif key == 83:  # flèche droite
                x += delta

    def upadte_mean_h_w(self):
        """ Update the value of mean h and w """
        for box_tracking in self.tracking_detection:

            box_tracking.mean_h.append(box_tracking.y2 - box_tracking.y1)
            box_tracking.mean_w.append(box_tracking.x2 - box_tracking.x1)
            box_tracking.mean_center.append((
                box_tracking.x1 + int((box_tracking.x2 - box_tracking.x1) / 2),
                box_tracking.y1 + int((box_tracking.y2 - box_tracking.y1) / 2)
                ))

            for list_max in [box_tracking.mean_h, box_tracking.mean_w, box_tracking.mean_center]:
                if len(list_max) > 5:
                    del(list_max[0])

    def update_xy_tracking(self):
        """ update the x and y value of box tracking """

        for tracking_detection in self.tracking_detection:
            if tracking_detection.x == 0 and tracking_detection.y == 0:
                continue
            tracking_detection.last_position.append((tracking_detection.x, tracking_detection.y))
            if len(tracking_detection.last_position) > self.last_position_max:
                del(tracking_detection.last_position[0])

        def compute_xy(box_trackings):

            for box_tracking in box_trackings:

                xp = float((0.5 * (box_tracking.x2 - box_tracking.x1)) + box_tracking.x1)
                yp = float(box_tracking.y2)

                # lissage hauteur
                if box_tracking.mean_h:
                    mean_h = sum(box_tracking.mean_h) / len(box_tracking.mean_h)
                    yp = float(box_tracking.y1 + mean_h)

                zone_result = []

                x, y = None, None
                for zone_detection in self.zone_detection[:-1]:
                    if zone_detection.plot_in_image((xp, yp)):
                        x, y = zone_detection.image_to_ground(xp, yp)
                        box_tracking.x = int(x)
                        box_tracking.y = int(y)
                        break

                if x is None:
                    x, y = self.zone_detection[-1].image_to_ground(xp, yp)
                    max_25 = int(0.25 * self.grid_max_value)
                    max_75 = int(0.75 * self.grid_max_value)
                    max_100 = self.grid_max_value

                    if 0 < x < max_25 and 0 < y < max_100:
                        x = -1

                    elif max_75 < x < max_100 and 0 < y < max_100:
                        y = max_100 + 1

                    if 0 < y < max_25 and 0 < x < max_100:
                        y = -1

                    elif max_75 < y < max_100 and 0 < x < max_100:
                        y = max_100 + 1

                    box_tracking.x = int(x)
                    box_tracking.y = int(y)

        compute_xy(self.tracking_detection)
        compute_xy(self.box_detection)

    def update_tracking_detection_occluded(self):
        """ Update occluded box tracking """
        result = {}
        for tracking_detection in self.tracking_detection:
            tracking_detection.occluded_by_box = []
            result[tracking_detection.tracking_id] = []

        boxes_sorted = sorted(self.tracking_detection, key=lambda b: b.y2, reverse=True)
        for i, boxA in enumerate(boxes_sorted):
            for j in range(i + 1, len(boxes_sorted)):
                boxB = boxes_sorted[j]  # boxB est plus éloignée (plus haute dans l'image)
                occ = boxA.intersection_aera(boxB)
                if occ:
                    result[boxB.tracking_id].append((boxA.x1,boxA.y1,boxA.x2,boxA.y2))

        for tracking_detection in self.tracking_detection:
            tracking_detection.occluded_by_box = result[tracking_detection.tracking_id]

    def get_new_tracking_index(self):
        """ return next tracking index """
        index = int(time.strftime("%H%M%S", time.localtime(time.time()))) * 10
        self.tracking_index += 1
        return int(index + self.tracking_index)

    def tracking_detection_save(self):
        """ init tracker index """
        max_tracking = 3
        history_track = self.get_history_track()

        for tracking_detection in self.tracking_detection:
            for field_track in self.tracker_fields:
                track_id = getattr(tracking_detection, field_track, 0)
                if not track_id:
                    continue

                for other_tracking_detection in self.tracking_detection:
                    not_track_ids = getattr(other_tracking_detection, 'not_' + field_track + 's', [])
                    if other_tracking_detection != tracking_detection:
                        if track_id not in not_track_ids:
                            not_track_ids.append(track_id)
                        if track_id in getattr(other_tracking_detection, field_track + 's'):
                            getattr(other_tracking_detection, field_track + 's').remove(track_id)

        for tracking_detection in self.tracking_detection:
            for field_track in self.tracker_fields:
                track_id = getattr(tracking_detection, field_track, 0)
                track_ids = getattr(tracking_detection, field_track + 's', [])
                not_track_ids = getattr(tracking_detection, 'not_' + field_track + 's', [])
                if not track_id:
                    continue

                if track_id not in not_track_ids and track_id not in track_ids:
                    track_ids.append(track_id)
                    if len(track_ids) > max_tracking:
                        del (track_ids[0])
                track_id = 0

            tracking_detection.state = 'tracking'

    def get_history_track(self):
        """ return a dic with """
        res = {}
        for field_track in self.tracker_fields:
            res[field_track] = {}

        for tracking_detection in self.tracking_detection:
            for field_track in self.tracker_fields:
                for tracking_history in getattr(tracking_detection, field_track + 's', []):
                    if tracking_history not in list(res[field_track].keys()):
                        res[field_track][tracking_history] = tracking_detection
        return res



    def compute_tracking2(self):
        """ compute new tracking with box_detection """

        # self.compute_tracker()
        self.tracking_detection_save()

        detection_track_ids = []
        box_detection_ok = []

        # --------- tracking update


        for box_detection in self.box_detection:
            for most_box_tracking in self.tracking_detection:
                if box_detection.track_id in detection_track_ids:
                    continue
                if box_detection.track_id in most_box_tracking.track_ids:
                    detection_track_ids.append(box_detection.track_id)

                    most_box_tracking.state = 'ok'
                    most_box_tracking.lost_frame = 0
                    most_box_tracking.tracking_ok += 1
                    most_box_tracking.update_by_boxdetection(box_detection)

                    box_detection.tracking_id = most_box_tracking.tracking_id
                    box_detection.state = 'ok'
                    box_detection_ok.append(box_detection)

        # --------- tracking lost
        for tracking_detection in self.tracking_detection:
            if tracking_detection.state == 'tracking':
                tracking_detection.state = 'lost'
                tracking_detection.lost_frame += 1
                tracking_detection.tracking_ko += 1

                if tracking_detection.track_id in detection_track_ids:
                    tracking_detection.track_id = 0
                for track_id in detection_track_ids:
                    if track_id in tracking_detection.track_ids:
                        del(tracking_detection.track_ids[track_id])

        # --------- tracking void
        for box_detection in self.box_detection:
            # Check if some lost tracking_detection is corresponding
            if box_detection in box_detection_ok:
                continue

            elif box_detection.track_id in detection_track_ids:
                box_detection.track_id = 0

        for box_detection in self.box_detection:
            # Check if some lost tracking_detection is corresponding
            if box_detection in box_detection_ok:
                continue
            elif not box_detection.track_id:
                # Check if tracking lost to associate
                tracking_detection_lost = self.get_tracking_lost_near_detection(box_detection)
                if tracking_detection_lost is not None:
                    self.update_tracking_detection(tracking_detection_lost, box_detection)
                    box_detection_ok.append(box_detection)

        # --------- tracking new
        for box_detection in self.box_detection:
            # Check if some lost tracking_detection is corresponding
            if box_detection in box_detection_ok:
                continue
            elif box_detection.track_id and self.box_detection_mini(box_detection):
                self.create_new_tracking_detection(box_detection)

        # -------- Delete old box_detection
        for tracking_detection in self.tracking_detection:
            if tracking_detection.lost_frame > int(1.5 * self.lost_frame_max):
                self.tracking_detection.remove(tracking_detection)

        # statistic
        self.update_statistic()

        # Update XY
        #self.update_tracking_detection_occluded()
        self.upadte_mean_h_w()

    def box_detection_mini(self, box_detection ):
        """ Return True , if box_detection is enought big to be tracked """
        res = False
        sreen_surface = self.camera_height * self.camera_width
        box_surface = (box_detection.y1 - box_detection.y2) * (box_detection.x1 - box_detection.x2)
        if box_surface / sreen_surface > self.surface_mini:
            res = True
        return res

    def update_tracking_detection(self, tracking_detection, box_detection):
        """ Update tracking by box detection """
        tracking_detection.state = 'ok'
        tracking_detection.lost_frame = 0
        tracking_detection.tracking_ok += 1
        tracking_detection.update_by_boxdetection(box_detection)
        box_detection.tracking_id = tracking_detection.tracking_id
        box_detection.state = 'ok'

    def create_new_tracking_detection(self, box_detection):
        """ Create new tracking with box detection """
        tracking_detection = tracking.TrackingDetection()
        tracking_detection.last_position_max = self.last_position_max
        tracking_detection.tracking_id = self.get_new_tracking_index()
        tracking_detection.state = 'new'
        tracking_detection.tracker_fields = self.tracker_fields
        tracking_detection.update_by_boxdetection(box_detection)
        self.tracking_detection.append(tracking_detection)
        return tracking_detection

    def get_tracking_lost_near_detection(self, box_detection):
        """ return list of tracking box lost near detection """
        tracking_detection_near = None
        for tracking_detection in self.tracking_detection:
            distance_near = self.lost_distance

            if tracking_detection.state == "lost":
                distance = box_detection.distance_tracking(tracking_detection)
                if distance < distance_near:
                    tracking_detection_near = tracking_detection

        return tracking_detection_near

    def update_statistic(self):
        """ update statistic of tracker """
        stat_ok_count = 0
        stat_last_count = 0
        stat_new_count = 0

        for tracking_detection in self.tracking_detection:
            if tracking_detection.state == 'ok':
                statistic_ok = self.stat_ok.copy()
                statistic_lost = self.stat_lost.copy()
                for i, field_track in enumerate(self.tracker_fields):
                    if getattr(tracking_detection, field_track):
                        statistic_ok[i] += 1
                    else:
                        statistic_lost[i] += 1
                self.stat_ok = statistic_ok
                self.stat_lost = statistic_lost
                stat_ok_count += 1

            elif tracking_detection.state == 'new':
                statistic_new = self.stat_new.copy()
                for i, field_track in enumerate(self.tracker_fields):
                    if getattr(tracking_detection, field_track):
                        statistic_new[i] += 1
                self.stat_new = statistic_new
                stat_new_count += 1

            elif tracking_detection.state == 'lost':
                statistic_lost = self.stat_lost.copy()
                for i, field_track in enumerate(self.tracker_fields):
                    statistic_lost[i] += 1
                self.stat_lost = statistic_lost
                stat_last_count += 1

        self.stat_ok_count = stat_ok_count
        self.stat_last_count = stat_last_count
        self.stat_new_count = stat_new_count

    def send_tracking_datas(self):
        """ send tracking data """
        return True
        tracking_fps = self.time_mean and float(1.0 / (sum(self.time_mean) / len(self.time_mean))) or 0.0

        tracking_datas = []

        for tracking_detection in self.tracking_detection:
            if tracking_detection.state in ['new', 'ok']:
                tracking_datas.append({
                    "tracking_id": int(tracking_detection.tracking_id),
                    "related_client_id": tracking_detection.related_client_id,
                    "posX": int(tracking_detection.x_pred),
                    "posY": int(tracking_detection.y_pred),
                    "state": tracking_detection.state,
                    "lost_frame": tracking_detection.lost_frame,
                    "zone": "game",
                    })

        data = {
            'tracking_fps': tracking_fps,
            'tracking_datas': tracking_datas,
            }

        try:
            t = threading.Thread(
                target=httpx.post,
                kwargs={"url": self.sending_url, "json": data, "timeout": 1.0}
            )
            t.start()
            # response = httpx.post(self.sending_url, json=data, timeout=1.0)
        except Exception as e:
            print("❌ Erreur lors de l'envoi :", e)

    def get_out_filename(self):
        """
        :return: new filename
        """
        # Récupère le dossier Vidéos de l'utilisateur
        home = os.path.expanduser("~")
        videos_dir = os.path.join(home, "Vidéos")

        # Génère un nom de fichier basé sur la date et l'heure
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"out_{date_str}.avi"

        # Construit le chemin complet
        file_path = os.path.join(videos_dir, filename)
        return file_path

    def main(self):
        """ launch captation """
        parser = argparse.ArgumentParser(description="Client HTTP en threading")
        parser.add_argument("--in_video", required=False, help="Path of the video training")
        parser.add_argument("--show", required=False, help="View camera screen")
        parser.add_argument("--output", required=False, help="Save video")
        parser.add_argument("--step", required=False, help="Step by step")
        parser.add_argument("--camera_usb_number", required=False, help="/dev/video usb number")

        args = parser.parse_args()

        if args.camera_usb_number:
            self.camera_usb_number = int(args.camera_usb_number)

        if args.in_video:
            self.init_video(args.in_video)
        else:
            self.init_camera()

        self.init_model()
        self.load_from_json()

        out = None
        if args.output:
            # Définir le codec et créer l'objet VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out_filename = self.get_out_filename()
            self.out_time = time.time()
            out = cv2.VideoWriter(out_filename, fourcc, 5.0, (self.camera_width, self.camera_height))

        sleep_key = False

        while True:
            start_time = time.time()
            # Capture une frame
            self.track_fps()

            self.get_camera_frame()
            camera_time = time.time()

            self.get_yolo_tracking()
            yolo_time = time.time()

            self.compute_tracking2()
            detect_time = time.time()

            if out is not None:
                if time.time() - self.out_time > 10 * 60 :
                    out.release()
                    out_filename = self.get_out_filename()
                    self.out_time = time.time()
                    out = cv2.VideoWriter(out_filename, fourcc, 5.0, (self.camera_width, self.camera_height))
                out.write(self.camera_frame)

            if args.show:

                # Dessiner les boîtes sur l'image originale
                frame = self.camera_frame
                #frame = self.show_grid(frame)
                frame = self.show_tracking(frame)


                if frame is not None:
                    cv2.imshow("Camera USB", frame)

            # Envoie les données
            self.send_tracking_datas()

            #out.write(frame)

            # Quitter avec la touche 'q'
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.save_to_json()
                break
            elif key == ord('a'):
                sleep_key = True
            elif key:
                self.key_press(key)

            if args.step == '2' and self.stat_new_count > 0:
                while key != ord('a'):
                    key = cv2.waitKey(1) & 0xFF

            while args.step == '1' and key != ord('a'):
                key = cv2.waitKey(1) & 0xFF

        # Libère les ressources
        if out is not None:
            out.release()
        self.stop_camera()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    detect = CameraDetection()
    detect.main()