from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    employee_id = fields.Many2one(
        comodel_name='pharmacy.employee',
        string='Employee ID',
        required=False
    )