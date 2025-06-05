from odoo import models, fields

class CartoonImage(models.Model):
    _name = "cartoon.image"
    _description = "Image"

    parent_id = fields.Many2one('cartoon.image', string='Parent Image')
    name = fields.Char(string='Name')
    directory = fields.Char(string='Directory')
    path = fields.Char(string='path')
    height = fields.Integer(string='Height')
    width = fields.Integer(string='Width')
    offset_x = fields.Integer(string='Offset X')
    offset_y = fields.Integer(string='Offset Y')
    path_id = fields.Many2one('cartoon.path', string='Backup')
    perceptual_hash = fields.Char(string='Perceptual Hash')
    thumbnail = fields.Binary(string='Thumbnail')
    shap = fields.Char(string='Shap')
