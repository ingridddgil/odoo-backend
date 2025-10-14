from odoo import fields, models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    sproject_id = fields.Many2one('project.project', 'Proyecto', domain="[('sale_order_id.id', '=', id)]")
    project_progress_ids = fields.One2many('project.sub.update', 'sale_order_id', string='Avances del Proyecto')

    service_status = fields.Selection(
        [('assig', 'Con OS'),
         ('no_assig', 'Sin OS')],
        string='Estatus de servicio', 
        required=True, tracking=True, default='no_assig')

    source_id = fields.Many2one(
        'sale.order.source',
        string='Origen',
        help='Especificar área que emite la orden',
        required=True,
        tracking=True,
    )

    destination_id = fields.Many2one(
        'sale.order.destination',
        string='Destino',
        help='Especificar el uso que se le da a la orden',
        required=True,
        tracking=True,
    )

    incident_id = fields.Many2one(
        'sale.order.incident',
        string='Incidencia',
        tracking=True
    )

 class SOCClassificationMixin(models.AbstractModel):
     _name = 'sale.order.classification.mixin'
     _description = 'Mixin común para catálogos de Sale Order'
     _order = 'name asc'
     _sql_constraints = [
         ('name_uniq', 'unique (name)', 'El nombre del origen debe ser único!'),
     ]

     name = fields.Char(string='Nombre', required=True, translate=True)
     color = fields.Integer(string='Color')
     active = fields.Boolean(string='Active', default=True)

class OrderSource(models.Model):
    #ORIGEN
    _inherit = 'sale.order.classification.mixin'
    _name = 'sale.order.source'
    _description = 'Origen de órdenes de venta'

class OrderDestination(models.Model):
    _inherit = 'sale.order.classification.mixin'
    _name = 'sale.order.destination'
    _description = 'Destinos de órdenes de venta'

class OrderIncident(models.Model):
    _inherit = 'sale.order.classification.mixin'
    _name = 'sale.order.incident'
    _description = 'Incidencias en órdenes de venta'