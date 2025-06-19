from odoo import models, fields, api
import os
import pwd

class CartoonTableau(models.Model):
    _name = "cartoon.tableau"
    _description = "Composite image made of multiple cartoon.image records"

    name = fields.Char("Name")


    # Individual image slots (can be used for specific layout)
    image_1_id = fields.Many2one('cartoon.image', string="snapshot")
    image_2_id = fields.Many2one('cartoon.image', string="Image 2")
    image_3_id = fields.Many2one('cartoon.image', string="Image 3")
    image_4_id = fields.Many2one('cartoon.image', string="Image 4")
    image_5_id = fields.Many2one('cartoon.image', string="Image 5")
    image_6_id = fields.Many2one('cartoon.image', string="Image 6")

    # Status of the tableau
    status = fields.Selection([
        ('draft', 'Draft'),
        ('snapshot', 'snapshot'),
        ('ready', 'Ready'),
        ('archived', 'Archived')
    ], default='draft', string="Status")

    image_sended = fields.Char('Image sending')

    @api.model
    def get_snapshot(self, directory=None):
        """ get snapshot """
        if not directory:
            uid = os.getuid()
            home_dir = pwd.getpwuid(uid).pw_dir
            directory = os.path.join(home_dir, 'Images/cartoon_images')

        tableau_ids = self.search([('status', 'in', ['snapshot', 'ready'])])
        if not tableau_ids:
            now = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tableau_ids |= tableau_ids.create({'name': 'tableau' + now, 'status': 'snapshot'})

        for tableau in tableau_ids:
            if tableau.status == 'snapshot' and not tableau.image_1_id:
                camera_ids = self.env['cartoon.camera'].search([('state', 'not in', ['draft', 'disabled'])])
                path_list = camera_ids.save_snapshot(directory=directory)

                for path in path_list:
                    image = self.env['cartoon.image'].search([('path', '=', path)], limit=1)
                    if image:
                        image.compute_face_count()
                        if image.face_ids:
                            tableau.image_1_id = image
                            tableau.status = 'ready'
        return True

    @api.model
    def get_next_image(self, tableau_id=None):
        """ take the camera and the face """
        res = {}
        # first send
        if not tableau_id or tableau_id == 0:
            tableau_ids = self.search([('status', '=', 'ready'), ('image_sended', '=', False), ('image_1_id', '!=', False)])
            if tableau_ids:
                tableau = tableau_ids[0]
                if tableau.image_1_id.faces_ids:
                    tableau.image_1_id.faces_ids[0].save_large_image()
                    res['path_image'] = tableau.image_1_id.faces_ids[0].path
                    res['tableau_id'] = tableau.id

        return res







