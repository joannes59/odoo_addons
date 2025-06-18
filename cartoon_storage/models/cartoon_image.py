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
    name = fields.Char(string='Name')
    directory = fields.Char(string='Directory')
    path = fields.Char(string='path', compute='_compute_path')
    image_type = fields.Char(string='type', compute='_compute_path')
    height = fields.Integer(string='Height')
    width = fields.Integer(string='Width')
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
                    _logger.warning(f"Erreur lors du chargement de l'image avec cv2 : {e}")
                    encoded_image = rec.get_black_encoded_image()
            else:
                encoded_image = rec.get_black_encoded_image()

            rec.encoded_image = encoded_image

