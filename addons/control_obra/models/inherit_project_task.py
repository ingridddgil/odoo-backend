from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class InheritProjectTask(models.Model):
    _inherit = 'project.task'
    
    sale_line_id = fields.Many2one(
        'sale.order.line', 'Sales Order Item', copy=False,
        compute="_compute_sale_line_id", store=True, readonly=False, index='btree_not_null',
        domain="[('is_service', '=', True), ('is_expense', '=', False), ('state', 'in', ['sale', 'done']), ('order_partner_id', '=?', partner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Sales order item that will be selected by default on the tasks and timesheets of this project,"
            " except if the employee set on the timesheets is explicitely linked to another sales order item on the project.\n"
            "It can be modified on each task and timesheet entry individually if necessary.")
    sale_order_id = fields.Many2one(string='Sales Order', related='sale_line_id.order_id', help="Sales order to which the project is linked.")
    
    delivered = fields.Float(string='Entregado', related='sale_line_id.qty_delivered')
    price_unit = fields.Float(string='Precio', related='sale_line_id.price_unit')
    total_pieces = fields.Float(string="Unidades (decimal)", related="sale_line_id.product_uom_qty")
    price_subtotal = fields.Float(string='Subtotal', compute='_subtotal')
    qty_invoiced = fields.Float(string="Facturado (unidades)", related="sale_line_id.qty_invoiced", store=True)
    disc =fields.Many2one(string='Especialidad', related='sale_line_id.product_id.categ_id', store=True)
    invoiced = fields.Float(string="Facturado", compute="_invoiced", store=True)
    
    sub_update_ids = fields.One2many('creacion.avances', 'task_id', 
                                      domain="[('project_id', '=', project_id), ('task_id.id', '=', id)]", string='Actualización de tareas')
    sub_update = fields.Many2one('creacion.avances', compute="_last_update", store=True)
    last_update = fields.Many2one('project.update', related='sub_update.update_id', string='Última actualización')
    sub_d_update = fields.Many2one('creacion.avances', compute="_d_update", string='Última actualización de tarea', store=True)
    last_d_update = fields.Many2one('project.update', related='sub_d_update.update_id', string='Última actualización modificada')
    last_update_date = fields.Datetime(related='last_d_update.write_date', string = 'Modificado por ult. vez')
    
    quant_progress = fields.Float(string="Piezas/Servicio", compute="_units", store=True)
    progress = fields.Integer(compute="_progress", string="Progreso", store=True)
    progress_percentage = fields.Float(compute="_progress_percentage", string="Progreso porcentual", store=True)
    
    is_complete = fields.Boolean(string="Complete", compute="_is_complete", default=False, store=True)

    #Campo para indicar que la tarea fue creada desde el modulo control de obra.
    is_control_obra = fields.Boolean(
        string="Tarea Control Obra",
        default=False,
        help="Indica que esta tarea fue creada desde el modulo control de obra.",
    )

    @api.depends('sale_line_id.qty_invoiced')
    def _invoiced(self):
        for u in self:
            u.invoiced = u.qty_invoiced * u.price_unit
    
    @api.model
    def _d_update(self):
        for u in self:
            u.sub_d_update = u.env['creacion.avances'].search([('project_id.id', '=', u.project_id.id), ('task_id.id', '=', u.id)], limit=1)
    
    @api.model
    def _check_to_recompute(self):
        return[id]
    
    @api.depends('sub_update_ids')
    def _last_update(self):
        for u in self:
            if not u.id:
                continue
            u.sub_update = u.env['creacion.avances'].search([('project_id.id', '=', u.project_id.id), ('task_id.id', '=', u.id)], order='id desc', limit=1)

    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'project_id.update_ids')
    def _units(self):
        for u in self:
            # Verifica si el registro está siendo creado (i.e., no tiene ID aún)
            if not u.id:
                continue

            progress = u.env['creacion.avances'].search([
                ('project_id.id', '=', u.project_id.id),
                ('task_id.id', '=', u.id)
            ]).mapped('unit_progress')

            # Asignar el valor del campo
            u.quant_progress = sum(progress)

            # Forzar la actualización del campo qty_delivered en la línea de venta
            if u.sale_line_id:
                u.sale_line_id.qty_delivered = u.quant_progress
    
    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'project_id.update_ids')
    def _progress(self):
        for u in self:
            if u.total_pieces > 0:
                progress = (u.quant_progress / u.total_pieces) * 100
            else:
                progress = 0
            u.progress = int(progress)
    
    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'project_id.update_ids')
    def _progress_percentage(self):
        for u in self:
            # Verifica si el registro está siendo creado (i.e., no tiene ID aún)
            if not u.id:
                continue
            u.progress_percentage = u.progress / 100
    
    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress', 'project_id.update_ids')
    def _subtotal(self):
        for u in self:
            if not u.id:
                continue
            subtotal = u.env['sale.order.line'].search([('id', '=', u.sale_line_id.id)]).mapped('price_subtotal')
            if subtotal:
                u.price_subtotal = float(subtotal[0])
            else:
                u.price_subtotal = 0.0

    @api.depends('sub_update_ids', 'sub_update_ids.unit_progress')
    def _is_complete(self):
        
        for task in self:
            if task.total_pieces == 0:

                continue
                
            if task.quant_progress == task.total_pieces:
                task.is_complete = True
                task.state = "1_done"
                task.stage_id = self.env['project.task.type'].search([
                    ('name', '=', 'Listo'),
                    ('project_ids', 'in', task.project_id.ids)
                ], limit=1)
            elif task.quant_progress > 0:
                task.is_complete = False
                task.stage_id = self.env['project.task.type'].search([
                    ('name', '=', 'En progreso'),
                    ('project_ids', 'in', task.project_id.ids)
                ], limit=1)
                task.state = "01_in_progress"
            else:
                task.is_complete = False
                task.stage_id = self.env['project.task.type'].search([
                    ('name', '=', 'Pendientes'),
                    ('project_ids', 'in', task.project_id.ids)
                ], limit=1)
                task.state = "04_waiting_normal"


    @api.model
    def update_task_status(self):
        tasks = self.env['project.task'].search([("sale_order_id", "!=", False)])
        for task in tasks:
            if task.quant_progress == task.total_pieces:
                task.is_complete = True
                task.state = "1_done"
                task.stage_id = self.env['project.task.type'].search([
                    ('name', '=', 'Listo'),
                    ('project_ids', 'in', task.project_id.ids)
                ], limit=1)
            elif task.quant_progress > 0:
                task.is_complete = False
                task.stage_id = self.env['project.task.type'].search([
                    ('name', '=', 'En progreso'),
                    ('project_ids', 'in', task.project_id.ids)
                ], limit=1)
                task.state = "01_in_progress"
            else:
                task.is_complete = False
                task.stage_id = self.env['project.task.type'].search([
                    ('name', '=', 'Pendientes'),
                    ('project_ids', 'in', task.project_id.ids)
                ], limit=1)
                task.state = "04_waiting_normal"

    @api.constrains('sub_update_ids')
    def _check_unique_items(self):
        for record in self:
            item_ids = record.item_ids.mapped('sub_update_ids')
            if len(item_ids) != len(set(item_ids)):
                raise ValidationError('No se pueden agregar ítems duplicados.')

    def write(self, vals):
        # 1. Almacena el proyecto anterior y la línea de venta antes del cambio
        old_projects = {task.id: task.project_id for task in self}
        old_sale_lines = {task.id: task.sale_line_id for task in self}

        # 2. Llama al método original
        res = super(InheritProjectTask, self).write(vals)

        # 3. Si el 'project_id' cambió, ejecuta la lógica de actualización
        if 'project_id' in vals:
            for task in self:
                old_project = old_projects.get(task.id)
                new_project = task.project_id

                # Procede solo si el proyecto realmente cambió
                if old_project and new_project and old_project.id != new_project.id:
                    sale_line = old_sale_lines.get(task.id)

                    if sale_line and sale_line.order_id:
                        # Re-establece la relación de la tarea con la línea de venta
                        task.write({'sale_line_id': sale_line.id})

                        # Actualiza el campo de proyecto en la ORDEN DE VENTA
                        sale_line.order_id.write({'project_id': new_project.id})

                        # VINCULA la orden de venta al nuevo proyecto
                        new_project.write({'sale_order_id': sale_line.order_id.id})

                        # AHORA DESVINCULA el proyecto de origen
                        # Verifica si el proyecto de origen tiene más tareas de la misma orden de venta
                        other_tasks = self.search([
                            ('project_id', '=', old_project.id),
                            ('sale_line_id.order_id', '=', sale_line.order_id.id)
                        ])

                        # Si no hay más tareas, desvincula la orden de venta del proyecto anterior
                        if not other_tasks:
                            old_project.write({'sale_order_id': False})

                        # Registra el cambio en el 'chatter'
                        message_body = _(
                            "La tarea %s ha sido movida del proyecto %s al proyecto %s. "
                            "Línea de Venta Asociada: %s"
                        ) % (task.name, old_project.name, new_project.name, sale_line.product_id.name)
                        sale_line.order_id.message_post(body=message_body, subject='Cambio de Proyecto en Tarea')

        return res

    def action_view_avances(self):
        return {
            'name': _("Avances de la Tarea"),
            'type': 'ir.actions.act_window',
            'res_model': 'creacion.avances',
            'view_mode': 'list,form',
            'domain': [('task_id', '=', self.id)],
            'context': {
                'default_task_id': self.id,
                'default_project_id': self.project_id.id,
                'create': True,
                'delete': False,
            },
            'flags':{'creatable': True},
            'target': 'current',
        }