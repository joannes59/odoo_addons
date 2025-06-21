from odoo import models, fields, api
import os
import pwd

class CartoonTableau(models.Model):
    _name = "cartoon.tableau"
    _description = "Composite image made of multiple cartoon.image records"

    name = fields.Char("Name")
    date = fields.Datetime('date')


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
        ('image_2', 'image_2'),
        ('image_3', 'image_3'),
        ('image_4', 'image_4'),
        ('image_5', 'image_5'),
        ('image_6', 'image_6'),
        ('archived', 'Archived')
    ], default='draft', string="Status")

    image_sended = fields.Char('Image sending')


    def get_snapshot(self, directory=None):
        """ get snapshot """
        if not directory:
            uid = os.getuid()
            home_dir = pwd.getpwuid(uid).pw_dir
            directory = os.path.join(home_dir, 'Images/cartoon_images')

        for tableau in self:
            if tableau.status == 'snapshot' and not tableau.image_1_id:
                camera_ids = self.env['cartoon.camera'].search([('state', 'not in', ['draft', 'disabled'])])
                image_ids = camera_ids.save_snapshot(directory=directory)

                for image in image_ids:
                    image.compute_face_count()
                    if image.face_ids and tableau.status == 'snapshot':
                        tableau.image_1_id = image
                        tableau.status = 'ready'
        return True

    @api.model
    def get_next_image(self, tableau_id=None):
        """ take the camera and the face """
        res = {}
        # first send
        if not tableau_id or tableau_id == 0:
            now = fields.Datetime.now().strftime("%Y%m%d_%H-%M-%S")
            tableau = self.create({'name': 'tableau_' + now, 'status': 'snapshot', 'date': fields.Datetime.now()})
            tableau.get_snapshot()
            res['tableau_id'] = tableau.id
        else:
            tableau = self.browse(tableau_id)
            if tableau.status == 'snapshot':
                tableau.get_snapshot()

            elif tableau.status == 'ready':
                if tableau.image_1_id.face_ids:
                    if not tableau.image_1_id.face_ids[0].path:
                        tableau.image_1_id.face_ids[0].save_large_image()
                    res['path_image'] = tableau.image_1_id.face_ids[0].path
                    res['tableau_id'] = tableau.id
                    tableau.status = 'image_2'

        print('----get_next_image-------', tableau_id, res)
        return res







