from odoo import fields, models, api


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    project_sub_updates = fields.One2many('creacion.avances', 'sale_order_id', string='Trabajos del Proyecto')

    @api.onchange('order_line')
    def _onchange_order_line_project(self):
        """
        Rellena el campo project_id en la cabecera
        basado en la selección en la primera línea.
        """
        if self.order_line and self.order_line[0].project_line_id:
            self.project_id = self.order_line[0].project_line_id
        else:
            self.project_id = False

    def action_open_change_name_wizard(self):
        self.ensure_one()
        return {
            'name': 'Asignar Nombre Pedido',
            'type': 'ir.actions.act_window',
            'res_model': 'renombrar.sale.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_nombre_nuevo': self.name,
                'active_id': self.id,
            },
        }