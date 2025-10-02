from odoo import fields, models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    sproject_id = fields.Many2one('project.project', 'Proyecto', domain="[('sale_order_id.id', '=', id)]")
    project_sub_updates = fields.One2many('project.sub.update', 'sale_order_id', string='Avances del Proyecto')

    serv_assig = fields.Selection(
        [('assig', 'Con OS'),
         ('no_assig', 'Sin OS')],
        string='Estatus de servicio', 
        required=True, tracking=True, default='no_assig')

    origen_id = fields.Many2one(
        'sale.order.origen',
        string='Origen',
        help='Especificar área que emite la orden',
        required=True,
        tracking=True,
    )

    dest_id = fields.Many2one(
        'sale.order.destino',
        string='Destino',
        help='Especificar el uso que se le da a la orden',
        required=True,
        tracking=True,
    )

    incidencia = fields.Many2one(
        'sale.order.incidencia',
        string='Incidencia',
        tracking=True
    )


class Origen(models.Model):
    _name = 'sale.order.origen'
    _description = 'Orígenes de órdenes de venta'
    _order = 'name asc'
    
    name = fields.Char(string='Nombre', required=True, translate=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(string='Activo', default=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'El nombre del origen debe ser único!'),
    ]


class Destino(models.Model):
    _name = 'sale.order.destino'
    _description = 'Destinos de órdenes de venta'
    _order = 'name asc'
    
    name = fields.Char(string='Nombre', required=True, translate=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(string='Activo', default=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'El nombre del destino debe ser único!'),
    ]


class Incidencia(models.Model):
    _name = 'sale.order.incidencia'
    _description = 'Incidencias en órdenes de venta'
    _order = 'name asc'
    
    name = fields.Char(string='Nombre', required=True, translate=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(string='Activo', default=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'El nombre de la incidencia debe ser único!'),
    ]