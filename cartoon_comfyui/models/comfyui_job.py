from odoo import models, fields, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class ComfyUIJob(models.Model):
    _name = "comfyui.job"
    _description = "ComfyUI job"

    name = fields.Char("Nom")
    payload = fields.Text("Payload JSON")  # le prompt à envoyer
    response = fields.Text("Réponse brute")
    job_id = fields.Char("ID de Job")
    workflow_id = fields.Many2one('comfyui.workflow', string='Workflow')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('error', 'Erreur'),
    ], string="Statut", default="draft")

    comfyui_url = fields.Char("URL Serveur", default="http://127.0.0.1:8188")

    @api.onchange('workflow_id')
    def onchange_workflow_id(self):
        """ update job """
        if self.workflow_id:
            self.payload = self.workflow_id.payload
            self.status = 'draft'

    def send_to_comfyui(self):
        for rec in self:
            if not rec.payload:
                continue

            url = f"{rec.comfyui_url.rstrip('/')}/prompt"
            #headers = {'Content-Type': 'application/json'}

            try:
                payload_dict = json.loads(rec.payload)
                p = {"prompt": payload_dict}
                data = json.dumps(p).encode('utf-8')

                res = requests.post(url, data=data)
                res.raise_for_status()

                data = res.json()
                rec.response = json.dumps(data, indent=2)
                rec.job_id = data.get("prompt_id")
                rec.status = "sent"

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
                    status = data.get(rec.job_id, {}).get('status')
                    if status.get('completed'):
                        rec.status = "done"
                        outputs = data.get(rec.job_id, {}).get('outputs')

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