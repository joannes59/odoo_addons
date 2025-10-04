import math

import cv2
import os
import time

from transformers import AutoImageProcessor, SiglipForImageClassification
import torch


KEYPOINTS_FACE = [0, 1, 2, 3, 4]
# Load model and processor
model_name = "prithivMLmods/Realistic-Gender-Classification"
model = SiglipForImageClassification.from_pretrained(model_name)
processor = AutoImageProcessor.from_pretrained(model_name)


class BoxDetection:
    def __init__(self,x1, y1, x2, y2, label, conf, class_id, track_id):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.label = label
        self.conf = conf
        self.class_id = class_id # Yolo classification 0 = personne
        self.track_id = track_id # Yolo tracking 0 = None

        self.keypoints = []

        self.tracking_ok = 0
        self.tracking_ko = 0

        self.tracking_id = 0
        self.state = "tracking"

        self.mean_h = []

        self.x = 0
        self.y = 0

    def distance_tracking(self, tracking_detection):
        """ return the distance """
        distance = math.sqrt((self.x - tracking_detection.x)**2 + (self.y - tracking_detection.y)**2)
        return distance

class TrackingDetection:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.last_position = []
        self.last_position_max = 5

        self.x1 = 0
        self.y1 = 0
        self.x2 = 0
        self.y2 = 0

        self.mean_w = []
        self.mean_h = []
        self.mean_center = []
        self.center_pred = (0, 0)

        self.x_pred = 0
        self.y_pred = 0

        self.x1_pred = 0
        self.y1_pred = 0
        self.x2_pred = 0
        self.y2_pred = 0

        self.x1_ok = 0
        self.y1_ok = 0
        self.x2_ok = 0
        self.y2_ok = 0

        self.occluded_by_box = []
        self.show_last_position = []
        self.label = 'new'
        self.class_id = 0 # Yolo classification 0 = personne

        self.track_id = 0 # Yolo tracking 0 = None
        self.track_ids = []

        self.keypoints = []

        self.tracker_fields = []
        self.not_track_ids = []
        self.not_track_boost_ids = []
        self.not_track_byte_ids = []
        self.not_track_ocsort_ids = []

        self.tracking_ok = 0
        self.tracking_ko = 0

        self.tracking_id = 0
        self.related_client_id = ''
        self.lost_frame = 0
        self.zone_xy = []
        self.state = 'new'
        self.conf = 0
        self.tracker = None
        
        self.facing = 'none'
        self.gender = 'none'
        self.face_x1 = 0
        self.face_y1 = 0
        self.face_x2 = 0
        self.face_y2 = 0


    def get_facing(self, tol_ratio=0.1):
        """
        keypoints : dict {id: [x, y]} avec 0=nez, 1=œil gauche, 2=œil droit, 3=oreille gauche, 4=oreille droite
        tol_ratio : tolérance relative (écart gauche/droite)
        tol_y     : tolérance en pixels pour la différence de hauteur yeux
        """
        facing = 'none'
        if self.keypoints:
            nose = self.keypoints[0]
            left_eye = self.keypoints[1]
            right_eye = self.keypoints[2]
            left_ear = self.keypoints[3]
            right_ear = self.keypoints[4]
            facing = 'none'

            if right_ear[0] < right_eye[0] < nose[0] and nose[0] < left_eye[0] < left_ear[0]:
                facing = 'front'

            if nose[0] - right_ear[0] > 2 * (left_ear[0] - nose[0]):
                facing += ' right'
            if left_ear[0] - nose[0] > 2 * (nose[0] - right_ear[0]):
                facing += ' left'

            if right_ear[0] > left_ear[0]:
                facing = 'back'

            if left_eye[1] > left_ear[1] or right_eye[1] > right_ear[1]:
                facing += ' down'

            if (nose[1] - left_eye[1] < left_ear[1] - nose[1]) or (nose[1] - right_eye[1] < right_ear[1] - nose[1]):
                facing += ' up'

            x_vals = []
            y_vals = []
            for plot in [left_eye, right_eye, left_ear, right_ear]:
                x_vals.append(plot[0])
                y_vals.append(plot[1])

            width = max(x_vals) - min(x_vals)
            hight = max(y_vals) - min(y_vals)
            center = (int(min(x_vals) + 0.5 * width), int(min(y_vals) + 0.5 * hight))

            if right_ear[0] < nose[0] and left_ear[0] < nose[0]:
                center_ear = - int((2 * nose[0] - right_ear[0] - left_ear[0]) / 4)
            elif right_ear[0] > nose[0] and  left_ear[0] > nose[0]:
                center_ear =  int((left_ear[0] + right_ear[0] - 2 * nose[0]) / 4)
            else:
                center_ear = 0


            self.face_x1 = int(min(x_vals) - 0.2 * width)
            self.face_y1 = int(center[1] - width)
            self.face_x2 = int(max(x_vals) + 0.2 * width)
            self.face_y2 = int(center[1] + width)

            if center_ear < 0:
                self.face_x1 += center_ear
            elif center_ear > 0:
                self.face_x2 += center_ear

            if self.face_x1 < self.x1:
                self.face_x1 = self.x1
            if self.face_x2 > self.x2:
                self.face_x2 = self.x2
            if self.face_y1 < self.y1:
                self.face_y1 = self.y1
            if self.face_y2 > self.y2:
                self.face_y2 = self.y2

        self.facing = facing

    def to_rgb(self, image):
        if len(image.shape) == 2:  # Gris
            return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 3:  # Couleur
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        elif image.shape[2] == 4:  # RGBA / BGRA
            return cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        else:
            raise ValueError("Format d'image non supporté")

    def get_gender(self, frame):
        """ return deepface analyse """
        if 'front' in self.facing and self.gender == 'none':
            self.gender = 'test'
            # Extraire le visage depuis la frame
            face_crop = frame[self.face_y1:self.face_y2, self.face_x1:self.face_x2]

            image = self.to_rgb(face_crop)
            inputs = processor(images=image, return_tensors="pt")

            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=1).squeeze().tolist()

            id2label = {"0": "female", "1": "male"}
            prediction = {id2label[str(i)]: round(probs[i], 3) for i in range(len(probs))}
            if prediction.get('female') > 0.6:
                self.gender = 'female'
            elif prediction.get('male') > 0.6:
                self.gender = 'male'
            else:
                self.gender = 'none'


    def validation_xy(self):
        """ Last validation  xy  values """
        pass

    def update_by_boxdetection(self, boxdetection):
        """ update value """
        self.x1 = boxdetection.x1
        self.y1 = boxdetection.y1
        self.x2 = boxdetection.x2
        self.y2 = boxdetection.y2

        self.x = boxdetection.x
        self.y = boxdetection.y

        self.class_id = boxdetection.class_id
        self.conf = boxdetection.conf
        self.keypoints = boxdetection.keypoints

        for field_track in self.tracker_fields:
            tracker_id = getattr(self, field_track, 0)
            not_tracker_ids = getattr(self, 'not_' + field_track + 's', 0)
            tracker_boxdetection_id = getattr(boxdetection, field_track, 0)
            if tracker_id not in not_tracker_ids:
                setattr(self, field_track, tracker_boxdetection_id)

    def intersection_aera(self, trackingbox):
        """ return intersection aera """
        xA = max(self.x1, trackingbox.x1)
        yA = max(self.y1, trackingbox.y1)
        xB = min(self.x2, trackingbox.x2)
        yB = min(self.y2, trackingbox.y2)

        if xB <= xA or yB <= yA:
            return 0.0  # pas d'intersection

        return (xB - xA) * (yB - yA)

    def get_bbox(self):
        """ return bbox """
        return (self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)


    def get_visible_y2(self):
        """ return bbox visible from x1,y1 """
        box = (self.x1, self.y1, self.x2, self.y2)
        for xybox in self.occluded_by_box:
            if xybox[1] > box[3]:
                box[3] = xybox[1]
        if box[1] > box[3]:
            box[3] = box[1]
        bbox = (box[0], box[1], box[2] - box[0], box[3] - box[1])
        return bbox

    def intersection_boxdetection(self, boxdetection):
        """ return % of surface with boxdetection"""
        surface = (self.x2 - self.x1) * (self.y2 - self.y1)
        if surface != 0.0:
            inter_w = max(0, min(self.x2, boxdetection.x2) - max(self.x1, boxdetection.x1))
            inter_h = max(0, min(self.y2, boxdetection.y2) - max(self.y1, boxdetection.y1))
            res = inter_w * inter_h / surface
        else:
            res = 0.0
        return int(100 * res)

