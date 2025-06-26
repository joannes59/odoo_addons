from odoo import models, fields, api
import json

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

    def get_default_parameter(self):
        """ return parameter """
        self.ensure_one()
        workflow = json.loads(self.payload)
        res = dict()
        for parameter in self.parameter_ids:
            res[parameter.name] = workflow[parameter.node]['inputs'][parameter.input_key]
        return res

    def action_download_json(self):
        """ return payload to file """
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_url',
            'name': 'Download',
            'url': f'/comfyui/workflow/download/{self.id}',
            'target': 'self',
        }
        return action