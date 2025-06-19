{
    'name': 'Cartoon Tableau',
    'version': '1.0',
    'depends': ['cartoon_storage', 'cartoon_camera', 'cartoon_comfyui', 'cartoon_deepface'],
    'author': 'joannes.landy@gmail.com',
    'category': 'Tools',
    'description': 'create image for installation les nuits des bassins.',
    'data': [
        # vues, sécurité si besoin
        "security/ir.model.access.csv",
        "views/cartoon_tableau_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
