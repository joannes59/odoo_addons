import base64
import os
import cv2
import uuid
from odoo import models, fields, api
from odoo.exceptions import UserError


class CartoonImageImportWizard(models.TransientModel):
    _name = 'cartoon.image.import.wizard'
    _description = 'Import Image Wizard'

    image_file = fields.Binary("Image", required=True)
    filename = fields.Char("Filename")

    path = fields.Char("Saved Path", readonly=True)

    def action_import(self):
        for wizard in self:
            action = True

            if not wizard.image_file or not wizard.filename:
                raise UserError("Veuillez sélectionner une image valide.")

            # Extension sécurisée
            ext = os.path.splitext(wizard.filename)[1].lower()
            if ext not in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
                raise UserError("Extension non supportée : %s" % ext)

            # Sauvegarder avec nom unique
            temp_dir = "/home/joannes/Images/cartoon_images"
            os.makedirs(temp_dir, exist_ok=True)
            unique_name = f"{uuid.uuid4().hex}{ext}"
            path = os.path.join(temp_dir, unique_name)

            with open(path, "wb") as f:
                f.write(base64.b64decode(wizard.image_file))

            img = cv2.imread(path)
            if img is not None:
                height, width = img.shape[:2]

                # Retourner le chemin
                wizard.path = path

                active_model = self.env.context.get('active_model', '?')
                active_id = self.env.context.get('active_id', 0)
                image_vals = {
                    'name': unique_name,
                    'directory': temp_dir,
                    'height': height,
                    'width': width,
                }
                if active_model == 'cartoon.image' and active_id:
                    image = self.env[active_model].browse(active_id)
                    image.write(image_vals)
                else:
                    image = self.env['cartoon.image'].create(image_vals)

                action = {
                    'type': 'ir.actions.act_window',
                    'name': 'Image',
                    'res_model': 'cartoon.image',
                    'view_mode': 'form',
                    'res_id': image.id,
                    'target': 'current',
                }

            return action
