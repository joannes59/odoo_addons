from odoo import models, fields, api
import json
import cv2
import os

class CartoonFace(models.Model):
    _name = 'cartoon.face'
    _description = 'Face Analysis Result'
    _order = "image_id desc, surface desc"

    image_id = fields.Many2one('cartoon.image', string="Image", required=True, ondelete='cascade', index=True)

    age = fields.Integer("Age")
    dominant_gender = fields.Selection([
        ('Man', 'Man'),
        ('Woman', 'Woman'),
        ('Other', 'Other'),
    ], string="Gender")

    dominant_emotion = fields.Char("Dominant Emotion")

    # Détail des émotions
    emotion_angry = fields.Float("Angry (%)")
    emotion_disgust = fields.Float("Disgust (%)")
    emotion_fear = fields.Float("Fear (%)")
    emotion_happy = fields.Float("Happy (%)")
    emotion_sad = fields.Float("Sad (%)")
    emotion_surprise = fields.Float("Surprise (%)")
    emotion_neutral = fields.Float("Neutral (%)")

    region_x = fields.Integer("Face X")
    region_y = fields.Integer("Face Y")
    region_w = fields.Integer("Width")
    region_h = fields.Integer("Height")
    surface = fields.Integer("Surface", compute="_compute_surface", store=True, index=True)
    path = fields.Char(string='path')

    def save_image(self, directory='/home/joannes/Images/cartoon_face'):
        """ save images """
        for face in self:
            if not face.image_id or not face.image_id.path:
                continue
            x, y, w, h = face.region_x, face.region_y, face.region_w, face.region_h
            if w <= 0 or h <= 0:
                continue

            img = cv2.imread(face.image_id.path)
            face_crop = img[y:y + h, x:x + w]

            os.makedirs(directory, exist_ok=True)
            filename = f"face_{face.id}.png"
            full_path = os.path.join(directory, filename)
            cv2.imwrite(full_path, face_crop)
            face.path = full_path

    def save_large_image(self, directory='/home/joannes/Images/cartoon_face'):
        """ save images """
        for face in self:
            if not face.image_id or not face.image_id.path:
                continue
            x, y, w, h = face.region_x, face.region_y, face.region_w, face.region_h
            if w <= 0 or h <= 0:
                continue

            x2 = int(x - 0.4 * w)
            y2 = int(y - 0.5 * h)
            x3 = int(x + 1.4 * w)
            y3 = int(y + 1.5 * h)

            if x2 < 0:
                x2 = 0
            if y2 < 0:
                y2 = 0
            if x3 > face.image_id.width:
                x3 = face.image_id.width
            if y3 > face.image_id.height:
                y3 = face.image_id.height

            img = cv2.imread(face.image_id.path)
            face_crop = img[y2:y3, x2:x3]

            os.makedirs(directory, exist_ok=True)
            filename = f"face_large_{face.id}.png"
            full_path = os.path.join(directory, filename)
            cv2.imwrite(full_path, face_crop)
            face.path = full_path

    @api.depends('region_w', 'region_h')
    def _compute_surface(self):
        """ Used to order """
        for face in self:
            face.surface = face.region_w * face.region_h

    def update_from_deepface_result(self, result, image):
        """
        Crée un enregistrement cartoon.face à partir d'un dict DeepFace
        """
        emotion = result.get("emotion", {})
        return self.create({
            'image_id': image.id,
            'age': int(result.get("age", 0)),
            'dominant_gender': result.get("dominant_gender", "Other"),
            'dominant_emotion': result.get("dominant_emotion", ""),
            'emotion_angry': emotion.get("angry", 0.0),
            'emotion_disgust': emotion.get("disgust", 0.0),
            'emotion_fear': emotion.get("fear", 0.0),
            'emotion_happy': emotion.get("happy", 0.0),
            'emotion_sad': emotion.get("sad", 0.0),
            'emotion_surprise': emotion.get("surprise", 0.0),
            'emotion_neutral': emotion.get("neutral", 0.0),

            'region_x': result.get("region", {}).get("x", 0),
            'region_y': result.get("region", {}).get("y", 0),
            'region_w': result.get("region", {}).get("w", 0),
            'region_h': result.get("region", {}).get("h", 0),

        })
