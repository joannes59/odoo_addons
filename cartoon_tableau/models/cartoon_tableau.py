from odoo import models, fields, api
import os
import pwd
import json
import random

import logging
_logger = logging.getLogger(__name__)

class CartoonTableau(models.Model):
    _name = "cartoon.tableau"
    _description = "Composite image made of multiple cartoon.image records"

    name = fields.Char("Name")
    parent_id = fields.Many2one('cartoon.tableau', string='Template')
    date = fields.Datetime('date')
    tableau_type = fields.Selection(
        [('draft', 'Draft'), ('template', 'Template'), ('normal', 'Normal')], string="Type", default="normal"
        )


    # Individual image slots (can be used for specific layout)

    image_1_id = fields.Many2one('cartoon.image', string="snapshot", copy=False)
    workflow_1 = fields.Many2one('comfyui.workflow', string="workflow 1")
    job_1 = fields.Many2one('comfyui.job', string="job 1", copy=False)
    time_1 = fields.Integer('Time 1 (cycle)')

    image_2_id = fields.Many2one('cartoon.image', string="Image 2", copy=False)
    workflow_2 = fields.Many2one('comfyui.workflow', string="workflow 2")
    job_2 = fields.Many2one('comfyui.job', string="job 2", copy=False)
    time_2 = fields.Integer('Time 2 (cycle)')

    image_3_id = fields.Many2one('cartoon.image', string="Image 3", copy=False)
    workflow_3 = fields.Many2one('comfyui.workflow', string="workflow 3")
    job_3 = fields.Many2one('comfyui.job', string="job 3", copy=False)
    time_3 = fields.Integer('Time 3 (cycle)')

    image_4_id = fields.Many2one('cartoon.image', string="Image 4", copy=False)
    workflow_4 = fields.Many2one('comfyui.workflow', string="workflow 4")
    job_4 = fields.Many2one('comfyui.job', string="job 4", copy=False)
    time_4 = fields.Integer('Time 4 (cycle)')

    image_5_id = fields.Many2one('cartoon.image', string="Image 5", copy=False)
    workflow_5 = fields.Many2one('comfyui.workflow', string="workflow 5")
    job_5 = fields.Many2one('comfyui.job', string="job 5", copy=False)
    time_5 = fields.Integer('Time 5 (cycle)')

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

    def button_test(self):
        """ Test workflow """
        self.ensure_one()
        if self.status == "draft":
            tableau_id = 0
        else:
            tableau_id = self.id
        res = self.get_next_image(tableau_id)
        _logger.info(f'-----button_test-----: {res}')

    @api.model
    def get_next_image(self, tableau_id=None):
        """ take the camera and the face """
        _logger.info(f'--get_next_image---tableau_id: {tableau_id}')
        res = {}
        # first send
        if not tableau_id or tableau_id == 0:
            now = fields.Datetime.now().strftime(" %Y%m%d_%H-%M-%S")
            template_ids = self.search([('tableau_type', '=', 'template')])
            tableau = template_ids[0].copy({'name': template_ids[0].name + now, 'status': 'snapshot',
                                            'tableau_type': 'normal',
                                            'parent_id': template_ids[0].id, 'date': fields.Datetime.now()})
            tableau.get_snapshot()
            res['tableau_id'] = tableau.id
        else:
            tableau = self.search([('id', '=', tableau_id)])
            if tableau:
                res['tableau_id'] = tableau.id
                template = tableau.parent_id or tableau

                if tableau.status == 'snapshot':
                    tableau.get_snapshot()

                elif tableau.status == 'ready':
                    if tableau.image_1_id.face_ids:
                        if not tableau.image_1_id.face_ids[0].path:
                            tableau.image_1_id.face_ids[0].save_large_image()

                        job_vals = {
                            'name': 'JOB' + tableau.name + 'image_2',
                            'workflow_id': template.workflow_1.id,
                            }
                        tableau.job_1 = self.env['comfyui.job'].create(job_vals)
                        parameter = {'origin_image': tableau.image_1_id.face_ids[0].path}
                        tableau.job_1.onchange_workflow_id()
                        tableau.job_1.parameter = json.dumps(parameter, indent=4)
                        tableau.job_1.update_paylod()
                        tableau.job_1.send_to_comfyui()


                        #res['path_image'] = tableau.image_1_id.face_ids[0].path
                        tableau.status = 'image_2'

                elif tableau.status == 'image_2':
                    tableau.job_1.check_job_status()
                    if tableau.job_1.status == 'pending':
                        pass
                    elif tableau.job_1.status == 'done':
                        images = tableau.job_1.get_local_images()
                        if images:
                            tableau.image_2_id = self.env['cartoon.image'].create_by_path(images[0])
                            tableau.image_2_id.put_transpary()
                            res['path_image'] = tableau.image_2_id.path
                            tableau.status = 'image_3'

                            job_vals = {
                                'name': 'JOB' + tableau.name + 'image_3',
                                'workflow_id': template.workflow_2.id,
                                }
                            tableau.job_2 = self.env['comfyui.job'].create(job_vals)
                            parameter = {'origin_image': tableau.image_2_id.path}
                            parameter['positive_text'] = tableau.create_face_prompt()

                            tableau.job_2.onchange_workflow_id()
                            tableau.job_2.parameter = json.dumps(parameter, indent=4)
                            tableau.job_2.update_paylod()
                            tableau.job_2.send_to_comfyui()

                elif tableau.status == 'image_3':
                    tableau.job_2.check_job_status()
                    if tableau.job_2.status == 'pending':
                        pass
                    elif tableau.job_2.status == 'done' and not tableau.image_3_id:
                        images = tableau.job_2.get_local_images()
                        if images:
                            tableau.image_3_id = self.env['cartoon.image'].create_by_path(images[0])
                            res['path_image'] = tableau.image_3_id.path
                    elif tableau.job_2.status == 'done' and tableau.image_3_id:
                        if tableau.time_2 > 0:
                            tableau.time_2 -= 1
                        else:
                            tableau.status = 'image_4'


                else:
                    res['tableau_id'] = 0
            else:
                res['tableau_id'] = 0

        _logger.info(f'----get_next_image---end-: {tableau_id} {res}')
        return res


    def create_face_prompt(self):
        """ Check genre and emotion """
        self.ensure_one()
        prompt = "Medieval and Renaissance portrait, charcoal drawing with intricate linework."
        if self.image_1_id.face_ids:
            face = self.image_1_id.face_ids[0]
            gender = ''
            condition = [('category', '=', 'recueil_arras')]

            if face.dominant_gender != 'Other':
                condition.append(('dominant_gender', '=', face.dominant_gender))
                prompt.replace('portrait', 'man portrait')

            if face.dominant_emotion:
                prompt += f"((( The dominant emotion is {face.dominant_emotion})))."

            if face.age:
                prompt += f"({face.age} old)."


            prompt_ids = self.env['comfyui.prompt'].search(condition)

            if prompt_ids:
                random_id = random.randint(0, len(prompt_ids) - 1)
                prompt += prompt_ids[random_id].prompt
        return prompt






