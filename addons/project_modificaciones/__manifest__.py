{
    'name': 'Modificaciones de Project',
    'author': 'Mauricio',
    'depends': ['base', 'sale', 'hr', 'project', 'sale_project'],
    'license': 'AGPL-3',
    'data': [
        # Archivos de seguridad primero
        'security/project_security.xml',
        'security/ir.model.access.csv',
        'security/ir.model.access.xml',

        # Archivos de vistas y menús después
        'views/project_task_extra_views.xml',
        'views/extra_project_update_views.xml',
        'views/project_extra_views.xml',
        
        'views/sale_order_ex.xml',
        'views/sale_config_settings_views.xml',       
        'views/project_tags_views.xml',
        'views/project_sub_update_views.xml',
        'views/supervisor_area_views.xml',
        'views/pending_services.xml',
        'views/pending_service_report.xml',
        'report/report_license_templates.xml',
        'views/menu_actions.xml',  # Este debe ser uno de los últimos
    ],
    'category': 'Technical',
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}