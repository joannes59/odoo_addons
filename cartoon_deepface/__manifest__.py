{
    'name': 'Cartoon DeepFace',
    'version': '1.0',
    'depends': ['cartoon_storage'],  # hérite du module existant
    'author': 'joannes.landy@gmail.com',
    'category': 'Tools',
    'description': 'Analyse faciale des images cartoon.',
    'data': [
        # vues, sécurité si besoin
        "security/ir.model.access.csv",
        "views/cartoon_image_views.xml",
    ],
    'installable': True,
    'auto_install': False,
}
