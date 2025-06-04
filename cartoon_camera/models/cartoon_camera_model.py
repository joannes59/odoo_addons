# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CartoonCameraModel(models.Model):
    _name = 'cartoon.camera.model'
    _description = 'Caméras model'

    name = fields.Char('Name', compute="compute_name")
    vendor_name = fields.Char('Vendor')
    model_name = fields.Char('Model')
    id_vendor = fields.Char('ID Vendor')
    id_model = fields.Char('ID Model')

    max_resolution = fields.Many2one('cartoon.resolution', 'Résolution maximale')
    description = fields.Text('Description')

    def compute_name(self):
        """ compose the name """
        for camera_model in self:
            camera_model.name = f'[{camera_model.vendor_name}] {camera_model.model_name}'



