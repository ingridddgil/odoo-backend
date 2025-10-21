from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)

class InheritSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    task_id = fields.Many2one(
        'project.task', 'Tarea', domain="[('sale_line_id.id', '=', id)]")

    avances_ids = fields.One2many(
        'creacion.avances',
        'sale_order_line_id', # Nombre del campo Many2one en creacion.avances
        string='Avances de la Línea'
    )

    def action_view_avances_from_line(self):
        """Abrir avances de esta línea desde cualquier contexto"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Avances - {self.name}',
            'res_model': 'creacion.avances',
            'view_mode': 'list,form',
            'domain': [('sale_order_line_id', '=', self.id)],
            'context': {
                'default_sale_order_line_id': self.id,
                'search_default_sale_order_line_id': self.id,
                'create': False
            },
            'target': 'current'
        }

    @api.depends('task_id.quant_progress')
    def _compute_qty_delivered(self):
        for u in self:
            u.qty_delivered = u.task_id.quant_progress
        res = super(InheritSaleOrderLine, self)._compute_qty_delivered()
        return res

    project_line_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        domain="[('is_proyecto_obra', '=', True)]",
    )

    # Método que permite rellenar de manera previa el campo project_line_id al crear una cotización nueva
    @api.model
    def default_get(self, fields_list):
        res = super(InheritSaleOrderLine, self).default_get(fields_list) or {}

        # Busca el proyecto VENTAS NUEVAS o crea uno si no existe
        default_project = self.env['project.project'].search([
            ('name', 'ilike', 'VENTAS NUEVAS'),
            ('is_proyecto_obra', '=', True)
        ], limit=1)

        if not default_project:
            # Crea el proyecto si no existe
            default_project = self.env['project.project'].create({
                'name': 'VENTAS NUEVAS',
                'is_proyecto_obra': True,
            })

        if default_project and 'project_line_id' in fields_list:
            res['project_line_id'] = default_project.id

        return res

    # Método que permite mover la tarea al proyecto seleccionado en la línea de orden de venta.
    # Instrucciones: Primero se debe realizar la cotización con el proyecto por defecto {VENTAS NUEVAS}, luego confirma la cotización y después de eso realizar la modificación en la linea al proyecto proyecto del supervisor correspondiente.
    def write(self, vals):
        # Primera parte: Manejo de partidas
        if 'order_id' in vals:
            orders_to_recalculate = self.mapped('order_id')
            result = super(InheritSaleOrderLine, self).write(vals)
            for order in orders_to_recalculate:
                order_lines = self.search([
                    ('order_id', '=', order.id)
                ], order='id')
                for index, line in enumerate(order_lines, 1):
                    partida_number = f"P{index:02d}"
                    line.partida = partida_number
            return result

        # Segunda parte: Manejo de proyectos (tu lógica original)
        old_projects = {line.id: line.project_line_id for line in self}
        res = super(InheritSaleOrderLine, self).write(vals)

        if 'project_line_id' in vals:
            for line in self:
                old_project = old_projects.get(line.id)
                new_project = line.project_line_id

                if old_project and new_project and old_project.id != new_project.id:
                    # 1. ACTUALIZA la tarea relacionada con el nuevo proyecto
                    if line.task_id:
                        line.task_id.write({
                            'project_id': new_project.id,
                        })

                    # 2. VINCULA la línea de venta al nuevo proyecto
                    new_project.write({'sale_line_id': line.id})

                    # 3. Desvincula el proyecto anterior si ya no tiene tareas
                    other_tasks = self.env['project.task'].search([
                        ('project_id', '=', old_project.id),
                        ('sale_line_id', '=', line.id)
                    ])
                    if not other_tasks:
                        old_project.write({'sale_line_id': False})
        return res

    qty_avances_delivered = fields.Float(
        string="Cantidad Entregada (Avances)",
        compute="_compute_qty_avances_delivered",
        store=True,
    )
    progress_percentage = fields.Float(
        string="Progreso (%)",
        compute="_compute_progress_percentage",
        store=True,
    )

    @api.depends('task_id.sub_update_ids.unit_progress')
    def _compute_qty_avances_delivered(self):
        for line in self:
            line.qty_avances_delivered = sum(line.task_id.sub_update_ids.mapped('unit_progress'))

    @api.depends('qty_avances_delivered', 'product_uom_qty')
    def _compute_progress_percentage(self):
        for line in self:
            if line.product_uom_qty > 0:
                line.progress_percentage = (line.qty_avances_delivered / line.product_uom_qty) * 100
            else:
                line.progress_pecentage = 0.0

    # Agregar el nuevo campo
    partida = fields.Char(
        string="Partida",
        copy=False,
        readonly=True,
        default="P00",
        help="Número de partida autoincremental por orden de venta"
    )

    # Sobrescribir el método create para generar el número de partida
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        for line in lines:
            if line.order_id:
                # Buscar todas las líneas de la misma orden
                order_lines = self.search([
                    ('order_id', '=', line.order_id.id)
                ], order='id')

                # Asignar números de partida secuenciales
                for index, order_line in enumerate(order_lines, 1):
                    partida_number = f"P{index:02d}"  # Formato P01, P02, etc.
                    order_line.partida = partida_number

        return lines

    # Método para reasignar partidas si se elimina una línea
    def unlink(self):
        orders_to_recalculate = self.mapped('order_id')
        result = super().unlink()

        # Recalcular partidas para las órdenes afectadas
        for order in orders_to_recalculate:
            order_lines = self.search([
                ('order_id', '=', order.id)
            ], order='id')

            for index, line in enumerate(order_lines, 1):
                partida_number = f"P{index:02d}"
                line.partida = partida_number

        return result