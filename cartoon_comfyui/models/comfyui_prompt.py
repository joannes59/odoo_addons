from odoo import models, fields, api
import json

class ComfyUIPrompt(models.Model):
    _name = 'comfyui.prompt'
    _description = 'ComfyUI Prompt'

    name = fields.Char('Name')
    prompt = fields.Text(string='Prompt', required=True)
    parameters = fields.Text(string='Parameters', default='{}')

    @api.model_create_multi
    def create(self, vals):
        # Validate JSON before creation
        if 'parameters' in vals:
            self._validate_json(vals['parameters'])
        return super().create(vals)

    def write(self, vals):
        # Validate JSON before update
        if 'parameters' in vals:
            self._validate_json(vals['parameters'])
        return super().write(vals)

    def _validate_json(self, json_str):
        try:
            json.loads(json_str)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in 'parameters'")
