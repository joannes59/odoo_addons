from odoo import models, fields, api

class ComfyUIWorkflow(models.Model):
    _name = "comfyui.workflow"
    _description = "Modèle de Workflow ComfyUI"

    name = fields.Char("Nom", required=True)
    description = fields.Text("Description")
    payload = fields.Text("Payload JSON", required=True)

    parameter_ids = fields.One2many('comfyui.workflow.parameter', 'workflow_id', string="Parameter")

    @api.onchange('payload')
    def update_parameter_ids(self):
        """ Update node number """
        for parameter in self.parameter_ids:
            parameter.onchange_meta_title()

