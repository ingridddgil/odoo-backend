{
    'name': 'Students',
    'version': '1.0',
    'summary': 'Student\'s information',
    'depends':[
        'portal',
        'mail'
    ],
    'data': [
        'view/student.xml',
        'view/emergency_contact.xml',
        'view/app_menu.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'application': True,
    'auto_install': False
}