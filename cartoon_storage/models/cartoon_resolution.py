# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CartoonResolution(models.Model):
    _name = 'cartoon.resolution'
    _description = 'Video Resolutions'
    _order = 'width, height'

    name = fields.Char('Nom', compute='_compute_name', store=True)
    width = fields.Integer('Largeur (px)', required=True)
    height = fields.Integer('Hauteur (px)', required=True)
    aspect_ratio = fields.Char('Ratio', compute='_compute_aspect_ratio', store=True)
    standard_name = fields.Selection([
        ('qvga', 'QVGA (320x240)'),
        ('vga', 'VGA (640x480)'),
        ('svga', 'SVGA (800x600)'),
        ('xga', 'XGA (1024x768)'),
        ('hd', 'HD (1280x720)'),
        ('fullhd', 'Full HD (1920x1080)'),
        ('4k', '4K (3840x2160)'),
        ('8k', '8K (7680x4320)'),
        ('custom', 'Custom')
    ], string='Standard', default='custom')
    readonly = fields.Boolean('readonly')

    @api.depends('width', 'height')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.width}x{rec.height}"

    @api.depends('width', 'height')
    def _compute_aspect_ratio(self):
        for rec in self:
            if rec.height > 0:
                ratio = rec.width / rec.height
                rec.aspect_ratio = f"{ratio:.2f}:1"
            else:
                rec.aspect_ratio = "0:1"


