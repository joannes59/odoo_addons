from odoo import http
from odoo.http import request, content_disposition
import json

class ComfyUIWorkflowController(http.Controller):

    @http.route('/comfyui/workflow/download/<int:workflow_id>', type='http', auth='user')
    def download_workflow_json(self, workflow_id, **kwargs):
        record = request.env['comfyui.workflow'].browse(workflow_id)
        if not record.exists():
            return request.not_found()

        try:
            data = json.loads(record.payload)  # Validate JSON
        except json.JSONDecodeError:
            return request.make_response("Invalid JSON", headers=[('Content-Type', 'text/plain')])

        filename = f"{record.name or 'workflow'}.json"
        headers = [
            ('Content-Type', 'application/json'),
            ('Content-Disposition', content_disposition(filename))
        ]
        return request.make_response(json.dumps(data, indent=2), headers=headers)
