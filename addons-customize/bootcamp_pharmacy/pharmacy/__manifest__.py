{
    'name': "Pharmacy",
    'author': "Ingrid Gil",
    'summary': "Pharmacy module",
    'depends': [
        'portal',
        'mail',
        'sale'
    ],
    'data': [
        'security/ir.model.access.csv',
        'view/employee.xml',
        'view/menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True
}