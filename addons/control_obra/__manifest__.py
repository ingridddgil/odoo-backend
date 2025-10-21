{
    "name": "Control De Obra",
    "version": "18.1",
    "author": "Mauricio, Antonio",
    "description": "Modelo para llevar el control de los servicios realizados",
    "depends": ["base", "sale", "hr", "project", "sale_project", "account", "hr_timesheet", "sale_management"],
    "data": [
        # Archivos de seguridad primero
        "security/ir.model.access.csv",
        "security/ir.model.access.xml",
        "security/project_security.xml",

        # Archivos de vistas y menús después
        "views/creacion_avances_views.xml",
        "views/asignar_avances_project_wizard_views.xml",
        "views/control_centro_trabajo_views.xml",
        "views/control_planta_views.xml",
        "views/inherit_project_task_views.xml",
        "views/inherit_project_update_views.xml",
        "views/inherit_project_project_views.xml",
        "views/inherit_sale_order_views.xml",
        "views/inherit_project_tags_views.xml",
        "views/inherit_sale_order_line_views.xml",
        "views/tipo_contacto_many2one_views.xml",
        "views/dashboard_sale_order_views.xml",
        "views/inherit_res_partner_views.xml",
        "views/inherit_hr_employee_views.xml",
        "views/inherit_product_template_views.xml",
        "views/renombrar_sale_order_wizard_views.xml",
        "views/menu_actions.xml",  # Este debe ser uno de los últimos
    ],
    "assets": {
        "web.assets_backend": [
            "control_obra/static/src/css/style.css",
        ],
    },
    "icon": "/control_obra/static/description/icon.png",
    "category": "Technical",
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
    "application": True,
}
