{
    'name': 'Cartoon ComfyUI Connector',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'cartoon_storage'],
    'category': 'Tools',
    'description': 'Permet d’envoyer des prompts à un serveur ComfyUI via API.',
    'installable': True,
    'auto_install': False,
    'application': False,
    'data': [
        "security/ir.model.access.csv",
        "views/comfyui_job_views.xml",
        "views/comfyui_workflow_views.xml",
    ],
}
