{
    'name': 'Cartoon Process Manager',  # Name of the module
    'version': '1.0',  # Version of the module
    'summary': 'Module to manage Python scripts and track processes',  # Short description
    'description': 'This module allows you to run Python scripts, such as a ComfyUI server, and track their processes.',  # Detailed description
    'author': 'joannes.landy@gmail.com',  # Author of the module
    'depends': ['cartoon_storage'],
    'data': [
        'security/ir.model.access.csv',  # Access control file
        'views/cartoon_process_views.xml',  # Views for the module
    ],
    'installable': True,  # Whether the module can be installed
    'application': True,  # Whether the module is an app (has a menu)
    'license': 'LGPL-3',
}