{
    'name': 'Modificaciones de Project',
    'summary': 'Ajustes compatibles con Odoo 18).',
    'version': '18.0.1.0.0',
    'author': 'Mauricio',
    'website': '',
    'category': 'Technical',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'sale',
        'hr',
        'project',
        'sale_project',
    ],
    'data': [
        # ── Seguridad primero ────────────────────────────────────────────────
        'security/project_security.xml',
        'security/ir.model.access.csv',
        # Nota: si necesitas ambos (CSV y XML) para accesos, está bien.
        # Asegúrate de no duplicar los mismos IDs en ambos archivos.
        'security/ir.model.access.xml',

        # ── Vistas / Reportes / Config ──────────────────────────────────────
        'views/project_task_extra_views.xml',
        'views/extra_project_update_views.xml',
        'views/project_extra_views.xml',
        'views/sale_order_ex.xml',
        'views/sale_config_settings_views.xml',
        'views/project_tags_views.xml',
        'views/project_sub_update_views.xml',
        'views/supervisor_area_views.xml',
        'views/pending_services.xml',

        # Reportes QWeb (plantillas y acciones)
        'views/pending_service_report.xml',
        'report/report_license_templates.xml',

        # ── Menús y acciones al final ───────────────────────────────────────
        'views/menu_actions.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
