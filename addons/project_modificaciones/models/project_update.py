from odoo import fields, models, api
from odoo.exceptions import ValidationError

class ProjectUpdate(models.Model):
    _inherit = 'project.update'
    _order = 'date desc'

    sub_update_ids = fields.One2many('project.sub.update', 'update_id')
    sale_current = fields.Float(string='Avance del subtotal', compute='_sale_current', store=True, default=0.0)
    sale_actual = fields.Float(string='Subtotal entregado', compute='_sale_actual', store=True, default=0.0)
    sale_total = fields.Float(string='Subtotal de la venta', compute='_sale_total', store=True, default=0.0)
    sale_missing = fields.Float(string='Subtotal faltante', compute='_sale_missing', store=True, default=0.0)
    
    sale_current_text = fields.Char(string='Avance del subtotal (pesos)', compute='_sale_current_text', store=True)
    sale_actual_text = fields.Char(string='Subtotal entregado (pesos)', compute='_sale_actual_text', store=True)
    sale_total_text = fields.Char(string='Subtotal de la venta (pesos)', compute='_sale_total_text', store=True)
    sale_missing_text = fields.Char(string='Subtotal faltante (pesos)', compute='_sale_missing_text', store=True)
    
    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'sub_update_ids.task_id')
    def _sale_current(self):
        for u in self:
            sale = u.env['project.sub.update'].search([('update_id.id', '=', u._origin.id)]).mapped('sale_current')
            u.sale_current = sum(sale)
    
    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'sub_update_ids.task_id')
    def _sale_actual(self):
        for u in self:
            sale = u.env['project.update'].search([('project_id.id', '=', u.project_id.id), ('id', '<=', u._origin.id)]).mapped('sale_current')
            u.sale_actual = sum(sale)
    
    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'sub_update_ids.task_id')
    def _sale_total(self):
        for u in self:
            sale = u.env['project.task'].search([('project_id.id', '=', u.project_id.id)]).mapped('price_subtotal')
            u.sale_total = sum(sale)
    
    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'sub_update_ids.task_id')
    def _sale_missing(self):
        for u in self:
            sale = u.sale_total - u.sale_actual
            u.sale_missing = sale

    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'sub_update_ids.task_id')
    def _sale_current_text(self):
        for u in self:
            sale = "%.2f" % u.sale_current
            value_len = sale.find('.')
            for i in range(value_len, 0, -1):
                sale = sale[:i] + ',' + sale[i:] if (value_len-i) % 3 == 0 and value_len != i else sale
            u.sale_current_text = '$' + sale
    
    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'sub_update_ids.task_id')
    def _sale_actual_text(self):
        for u in self:
            sale = "%.2f" % u.sale_actual
            value_len = sale.find('.')
            for i in range(value_len, 0, -1):
                sale = sale[:i] + ',' + sale[i:] if (value_len-i) % 3 == 0 and value_len != i else sale
            u.sale_actual_text = '$' + sale
    
    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'sub_update_ids.task_id')
    def _sale_total_text(self):
        for u in self:
            sale = "% .2f" % u.sale_total
            value_len = sale.find('.')
            for i in range(value_len, 0, -1):
                sale = sale[:i] + ',' + sale[i:] if (value_len-i) % 3 == 0 and value_len != i else sale
            u.sale_total_text = '$' + sale

    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'sub_update_ids.task_id')
    def _sale_missing_text(self):
        for u in self:
            sale = "% .2f" % u.sale_missing
            value_len = sale.find('.')
            for i in range(value_len, 0, -1):
                sale = sale[:i] + ',' + sale[i:] if (value_len-i) % 3 == 0 and value_len != i else sale
            u.sale_missing_text = '$' + sale
    