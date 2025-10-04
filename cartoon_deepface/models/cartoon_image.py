from odoo import models, fields, api
import cv2
import base64
import logging
import numpy as np
from deepface import DeepFace

_logger = logging.getLogger(__name__)

class CartoonImage(models.Model):
    _inherit = 'cartoon.image'

    face_count = fields.Integer(string='Number of face', index=True)
    face_data = fields.Text(string='Analyse face JSON')
    face_ids = fields.One2many('cartoon.face', 'image_id', string='Faces')

    def compute_face_count(self):
        for image in self:
            image.face_count = 0
            image.face_data = ""
            if not image.path:
                continue
            try:
                img = cv2.imread(image.path)
                if img is None:
                    _logger.warning(f"Impossible de lire l'image {image.path}")
                    continue

                # Appel DeepFace
                result = DeepFace.analyze(img_path=image.path, actions=['age', 'gender', 'emotion'], enforce_detection=False)
                if isinstance(result, list):  # DeepFace v1.x

                    image.face_data = str(result)
                    image.face_ids.unlink()
                    for face in result:
                        face_confidence = face.get('face_confidence', 0.0)
                        if face_confidence > 0.9:
                            image.face_ids.update_from_deepface_result(face, image)

                    image.face_count = len(image.face_ids)

            except Exception as e:
                _logger.warning(f"Erreur DeepFace sur {image.path} : {e}")


    @api.depends('path', 'image_type', 'face_ids')
    def _compute_encoded_image(self):
        for image in self:
            if image.path and image.image_type:
                try:
                    img = cv2.imread(image.path)
                    if img is not None:
                        for face in image.face_ids:
                            x = face.region_x
                            y = face.region_y
                            w = face.region_w
                            h = face.region_h
                            gender = face.dominant_gender or "?"
                            age = str(face.age) if face.age else "?"
                            emotion = face.dominant_emotion or "?"
                            label = f"{gender}, {age}, {emotion}"

                            # Couleur (B, G, R) + épaisseur 2px
                            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 1)

                            # Texte sous le rectangle
                            font = cv2.FONT_HERSHEY_SIMPLEX
                            font_scale = 0.5
                            thickness = 1
                            text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
                            text_x = x
                            text_y = y + h + text_size[1] + 5
                            # Texte en noir
                            cv2.putText(
                                img,
                                label,
                                (text_x, text_y),
                                font,
                                font_scale,
                                (0, 255, 0),
                                thickness,
                                cv2.LINE_AA
                            )

                        _, buffer = cv2.imencode(f'.{image.image_type}', img)
                        encoded_image = base64.b64encode(buffer).decode('utf-8')
                    else:
                        encoded_image = image.get_black_encoded_image()
                except Exception as e:
                    _logger.warning(f"Error when loaded image with cv2 : {e}")
                    encoded_image = image.get_black_encoded_image()
            else:
                encoded_image = image.get_black_encoded_image()

            image.encoded_image = encoded_image