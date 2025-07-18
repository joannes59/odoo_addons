from odoo import models, fields, api
import requests
import json
import logging
import os

_logger = logging.getLogger(__name__)

class ComfyUIJob(models.Model):
    _name = "comfyui.job"
    _description = "ComfyUI job"

    name = fields.Char("Nom")
    payload = fields.Text("Payload JSON")  # le prompt à envoyer
    parameter = fields.Text("Parameter JSON")  # le
    response = fields.Text("Response")
    job_id = fields.Char("Job ID")
    workflow_id = fields.Many2one('comfyui.workflow', string='Workflow')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string="Statut", default="draft")

    comfyui_url = fields.Char("URL Serveur", default="http://127.0.0.1:8188")



    @api.onchange('workflow_id')
    def onchange_workflow_id(self):
        """ update job """
        if self.workflow_id:
            self.payload = self.workflow_id.payload
            self.status = 'draft'
            self.response = False
            self.parameter = json.dumps(self.workflow_id.get_default_parameter(), indent=4)
        else:
            self.payload = False
            self.status = 'draft'
            self.parameter = False
            self.response = False

    def update_paylod(self):
        """ Update payload with parameter """
        self.ensure_one()
        if self.parameter and self.payload and self.workflow_id:
            job_parameter = json.loads(self.parameter)
            payload = json.loads(self.payload)
            for parameter in self.workflow_id.parameter_ids:
                if parameter.name in list(job_parameter.keys()):
                    payload[parameter.node]['inputs'][parameter.input_key] = job_parameter[parameter.name]
            self.payload = json.dumps(payload, indent=4)

    def send_to_comfyui(self):
        for rec in self:
            if not rec.payload:
                continue

            url = f"{rec.comfyui_url.rstrip('/')}/prompt"
            #headers = {'Content-Type': 'application/json'}

            try:
                rec.update_paylod()
                payload_dict = json.loads(rec.payload)
                p = {"prompt": payload_dict}
                data = json.dumps(p).encode('utf-8')

                res = requests.post(url, data=data)
                res.raise_for_status()

                data = res.json()
                rec.response = json.dumps(data, indent=4)
                rec.job_id = data.get("prompt_id")
                rec.status = "sent"
                rec.response = '{}'
            except Exception as e:
                _logger.warning(f"Erreur envoi ComfyUI : {e}")
                rec.response = str(e)
                rec.status = "error"


    def check_job_status(self):
        for rec in self:
            if not rec.job_id:
                continue

            url = f"{rec.comfyui_url.rstrip('/')}/history/{rec.job_id}"
            try:
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    status = data.get(rec.job_id, {}).get('status', {})
                    if status.get('completed'):
                        rec.status = "done"
                    else:
                        rec.status = "pending"

                    rec.response = json.dumps(data, indent=4)

                elif res.status_code == 404:
                    rec.status = "pending"
                else:
                    rec.status = "error"
            except Exception as e:
                rec.response = str(e)
                rec.status = "error"

    def get_outputs(self):
        """ get output response """
        self.ensure_one()
        outputs = json.loads(self.response).get(self.job_id, {}).get('outputs', {})
        return outputs

    def get_local_output_path(self):
        """ return the path of comfyui output """
        home_dir = os.path.expanduser("~")
        return home_dir + '/ComfyUI/output/'

    def get_local_images(self):
        """ return node output images """
        self.ensure_one()
        outputs = self.get_outputs()
        output_path = self.get_local_output_path()
        res = []
        for node in outputs:
            images = outputs[node].get('images', [])
            for image in images:
                if image.get('type', '?') == 'output':
                    res.append(output_path + image['filename'])
        # http://192.168.0.101:8188/api/view?filename=ComfyUI_temp_qtnnd_00299_.png&subfolder=&type=temp
        return res
