from odoo import api, fields, models


class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    cliente_id = fields.Many2one(
        'res.partner',
        string='Cliente',
    )

