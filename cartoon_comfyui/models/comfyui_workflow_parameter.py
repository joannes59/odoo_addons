from odoo import models, fields, api
import json

class ComfyUIWorkflowParameter(models.Model):
    _name = "comfyui.workflow.parameter"
    _description = "Parameter ComfyUI workflow"

    name = fields.Char("parameter", required=True)
    class_type = fields.Char("Class type")
    meta_title = fields.Char("Meta title", required=True)
    input_key = fields.Char("Input key", required=True)
    input_type = fields.Char("type")
    node = fields.Char("ID node")
    workflow_id = fields.Many2one("comfyui.workflow", string="Workflow", required=True, ondelete="cascade")

    @api.onchange('meta_title')
    def onchange_meta_title(self):
        """ complete node info """
        if self.workflow_id and self.workflow_id.payload:
            workflow = json.loads(self.workflow_id.payload)
            for node in list(workflow.keys()):
                if workflow[node].get('_meta', {}).get('title', '?') == self.meta_title:
                    self.class_type = workflow[node].get('class_type')
                    self.node = node

                    if not self.name:
                        self.name = self.meta_title
                    if not self.input_key:
                        for input_key in list(workflow[node]['inputs'].keys()):
                            if input_key in ['image', 'text', 'filename_prefix']:
                                self.input_key = input_key
                    if self.input_key:
                        self.input_type = str(type(workflow[node]['inputs'][self.input_key]).__name__)


    @api.onchange('input_key')
    def onchange_input_key(self):
        """ update the type """
        if self.input_key and self.node:
            try:
                self.input_type = str(type(workflow[node]['inputs'][self.input_key]).__name__)
            except:
                self.input_type = False
        else:
            self.input_type = False
