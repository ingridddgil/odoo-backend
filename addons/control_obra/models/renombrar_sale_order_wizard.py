from odoo import api, fields, models

class RenombrarSaleOrderWizard(models.TransientModel):
    _name = 'renombrar.sale.order.wizard'
    _description = 'RenombrarSaleOrderWizard'

    nombre_nuevo = fields.Char(
        string="Nombre Pedido",
        required=True,
    )

    def action_confirm_and_rename(self):
        self.ensure_one()
        # Obtenemos la orden de venta activa
        active_id = self.env.context.get('active_id')
        sale_order = self.env['sale.order'].browse(active_id)

        # P1. Cambiar el nombre
        sale_order.write({'name': self.nombre_nuevo})

        # P2. Llamar a la acción original de confirmación
        return sale_order.with_context(skip_rename_wizard=True).action_confirm()