from odoo import models, fields, api
import os
import base64
import logging
import cv2
import numpy as np

_logger = logging.getLogger(__name__)

cv2_supported_extensions = ["bmp", "dib", "jpeg", "jpg", "jpe", "jp2", "png", "webp", "pbm", "pgm", "ppm",
                            "sr", "ras", "tiff", "tif", "exr", "hdr", "pic"]


class CartoonImage(models.Model):
    _name = "cartoon.image"
    _description = "Image"

    parent_id = fields.Many2one('cartoon.image', string='Parent Image')
    name = fields.Char(string='Name', index=True)
    directory = fields.Char(string='Directory')
    path = fields.Char(string='path', compute='_compute_path', store=True, index=True)
    image_type = fields.Char(string='type', compute='_compute_path')
    height = fields.Integer(string='Height')
    width = fields.Integer(string='Width')
    channels = fields.Integer(string='channels')
    offset_x = fields.Integer(string='Offset X')
    offset_y = fields.Integer(string='Offset Y')
    path_id = fields.Many2one('cartoon.path', string='Backup')
    perceptual_hash = fields.Char(string='Perceptual Hash')
    thumbnail = fields.Binary(string='Thumbnail')
    shap = fields.Char(string='Shap')

    encoded_image = fields.Binary(
        string='Preview',
        compute='_compute_encoded_image',
        store=False,  # Not stored in database, computed on-the-fly
    )

    @api.depends('directory', 'name')
    def _compute_path(self):
        for record in self:
            if record.name:
                image_type = record.name.split('.')[-1]
                if image_type in cv2_supported_extensions:
                    record.image_type = image_type
                else:
                    record.image_type = False
            else:
                record.image_type = False

            if record.directory and record.name:
                record.path = os.path.join(record.directory, record.name)
            else:
                record.path = False

    def unlink(self):
        for record in self:
            if record.path and os.path.isfile(record.path):
                try:
                    os.remove(record.path)
                    # Check and delete the parent directory if empty
                    directory = os.path.dirname(record.path)
                    if os.path.isdir(directory) and not os.listdir(directory):
                        os.rmdir(directory)
                        
                except Exception as e:
                    _logger.warning(f"Failed to delete file {record.path}: {e}")
        return super(CartoonImage, self).unlink()


    def get_black_encoded_image(self):
        """ return black image """
        self.ensure_one()
        frame = np.zeros((self.height or 480, self.width or 640, 3), dtype=np.uint8)
        image_type = self.image_type or "jpg"
        _, buffer = cv2.imencode(f'.{image_type}', frame)
        encoded_image = base64.b64encode(buffer).decode('utf-8')
        return encoded_image

    @api.depends('path', 'image_type')
    def _compute_encoded_image(self):
        for rec in self:
            if rec.path and rec.image_type:
                try:
                    img = cv2.imread(rec.path)
                    if img is not None:
                        _, buffer = cv2.imencode(f'.{rec.image_type}', img)
                        encoded_image = base64.b64encode(buffer).decode('utf-8')
                    else:
                        encoded_image = rec.get_black_encoded_image()
                except Exception as e:
                    _logger.warning(f"Error when loaded image with cv2 : {e}")
                    encoded_image = rec.get_black_encoded_image()
            else:
                encoded_image = rec.get_black_encoded_image()

            rec.encoded_image = encoded_image

    @api.model
    def create_by_path(self, full_path):
        """ create record with the path """
        name = os.path.basename(full_path)
        directory = os.path.dirname(full_path)
        image = self.create({'name': name, 'directory': directory})
        image.check_size()
        return image

    def check_size(self):
        """ compute the size of the image """
        for image in self:
            img = cv2.imread(image.path)
            height, width, channels = img.shape
            image.height = height
            image.width = width
            image.channels = channels

    def gray_color(self):
        """ put image in gray color """
        for record in self:
            image = cv2.imread(record.path)
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            cv2.imwrite("image_grayscale.jpg", gray_image)

    def put_transpary(self):
        # Charger l'image avec OpenCV en mode couleur (et alpha si existant)
        for record in self:
            image = cv2.imread(record.path, cv2.IMREAD_UNCHANGED)

            if image.shape[2] == 4:  # Si l'image possède un canal alpha
                # Séparer les canaux BGR et Alpha
                bgr = image[:, :, :3]
                alpha_original = image[:, :, 3]  # Extraire le canal alpha existant
                # Convertir BGR en niveaux de gris
                grayscale = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

                # Additionner les valeurs du canal de gris avec le canal alpha existant
                alpha = np.minimum(alpha_original, 255 - grayscale)
                #alpha = np.clip(alpha, 0, 255)
                # Créer une nouvelle image RGBA en combinant les niveaux de gris avec le canal alpha
            else:
                # Si l'image est en RGB (sans alpha)
                grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                alpha = 255 - grayscale.copy()  # Le canal alpha est basé sur les niveaux de gris

            #rgba = cv2.merge([grayscale, grayscale, grayscale, alpha])
            rgba = cv2.merge([grayscale, grayscale, grayscale, alpha])

            # Enregistrer l'image en PNG (avec transparence)
            cv2.imwrite(record.path, rgba)


