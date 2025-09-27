import math


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

            if right_ear[0] < right_eye[0] < nose[0] and nose[0] < left_eye[0] < left_ear[0]:
                facing = 'front'
            elif right_ear[0] > left_ear[0]:
                facing = 'back'
            else:
                if right_ear[0] < nose[0] and right_ear[0] < nose[0]:
                    facing = 'left'
                elif right_ear[0] > nose[0] and right_ear[0] > nose[0]:
                    facing = 'right'

        self.facing = facing

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

