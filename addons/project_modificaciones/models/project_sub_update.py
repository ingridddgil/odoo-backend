from odoo import fields, models, api
from odoo.exceptions import ValidationError

class ProjectSubUpdate(models.Model):
    _name = 'project.sub.update'
    _description: 'Avances fisicos'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('no_fact', 'No facturado'),
        ('fact', 'Facturado'),
        ('inc', 'Incobrable'),
    ], string='Estado', copy=False, default='no_fact', tracking=True)
    
    project_id = fields.Many2one('project.project', string='Proyecto', compute='_project_id', store=True)
    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta', related='project_id.sale_order_id', store=True)
    incidencia = fields.Many2one('sale.order.incidencia', string="Incidencia", related='sale_order_id.incidencia', store=True)
    


    task_id = fields.Many2one('project.task', domain=
                              "[('project_id', '=', project_id), ('is_complete', '=', False)]",
                              string="Tarea")
    cliente = fields.Many2one(string="Cliente", related='project_id.partner_id', store=True, )
    update_id = fields.Many2one('project.update', 'Actualización', ondelete='cascade')
    proj = fields.Many2one(related='update_id.project_id', store=True)
    projid = fields.Integer(related='proj.id', string='ID del proyecto', store=True)
    projname = fields.Char(related='proj.name', string='Nombre del proyecto', store=True)
    analitica = fields.Many2one(string="Analitica", related='project_id.analytic_account_id')
    prev_progress = fields.Integer(related="task_id.progress", string="Current Progress", default=0)
    quant_total = fields.Float(related="task_id.total_pieces", default=0.0)
    unit_progress = fields.Float(string="Avance de unidades", default=0.0)
    quant_progress = fields.Float(string="Unidades entregadas", compute="_quant_progress", store=True, default=0.0)
    virtual_quant_progress = fields.Float(string="Unidades entregadas (virtual)", compute="_virtual_quant_progress", default=0.0)
    actual_progress = fields.Integer(compute="_actual_progress", string="Avance", default=0)
    actual_progress_percentage = fields.Float(compute="_actual_progress_percentage", string="Avance porcentual", default=0.0)
    total_progress = fields.Integer(string="Progreso total", compute="_total_progress", store=True, default=0)
    virtual_total_progress = fields.Integer(string="Progreso total (virtual)", compute="_virtual_total_progress", default=0)
    total_progress_percentage = fields.Float(compute="_total_progress_percentage")
    missing_quant = fields.Float(string="Unidades faltantes", compute="_missing_quant")
    sale_current = fields.Float(string="Avance del subtotal", compute="_sale_current", store=True)
    sale_actual = fields.Float(string="Subtotal entregado", compute="_sale_actual", store=True)
    sale_total = fields.Float(string="Subtotal de la venta", compute="_sale_total", store=True)
    sale_missing = fields.Float(string="Subtotal faltante", compute="_sale_missing", store=True)
    sale_current_text = fields.Char(string='Avance del subtotal (pesos)', compute='_sale_current_text', store=True)
    sale_actual_text = fields.Char(string='Subtotal entregado (pesos)', compute='_sale_actual_text', store=True)
    sale_total_text = fields.Char(string='Subtotal de la venta (pesos)', compute='_sale_total_text', store=True)
    sale_missing_text = fields.Char(string='Subtotal faltante (pesos)', compute='_sale_missing_text', store=True)
    task_name = fields.Char(related="task_id.name", string="Nombre de la tarea")
    date = fields.Date(related='update_id.date', store=True, string="Fecha")
    datefact = fields.Date(string="Fecha de factura", store=True)
    factura= fields.Many2one('account.move', string="Factura", domain="[('state', '=', 'posted'), ('move_type', '=', 'out_invoice')]")
    responsible_id = fields.Many2one('hr.employee', string="Responsable", domain="[('supervisa', '=', True)]")
    domain = fields.Char(string="dominio", compute="_dom")
    color = fields.Integer(related='update_id.color', string="Color")
    estado = fields.Selection(related='update_id.status', string="Estado tarea")
    serv_assig = fields.Selection(
        string='Estatus de servicio',
        selection=[('assig', 'Con OS'), ('no_assig', 'Sin OS')],
        compute='_compute_serv_assig_computed',
        store=True,  # Asegúrate de que esté almacenado
    )

    @api.depends('sale_order_id.serv_assig')
    def _compute_serv_assig_computed(self):
        for record in self:
            record.serv_assig = record.sale_order_id.serv_assig
        
    disciplina=fields.Many2one(string="Especialidad", related='task_id.disc', store=True)
    invoiced = fields.Float(string="Facturado", related='task_id.invoiced', store=True)
    is_invoiced = fields.Boolean(string="Facturado", default=False, help="Indica si este avance ya ha sido facturado")
    estimado = fields.Boolean(string="Estimado", default=False, help="Indica si este avance ya ha sido estimado")
    avanceparc = fields.Char(string='Avance parcial')
    cotizacion = fields.Char(string='# Cotización')
    om = fields.Char(string='# OM')
    supervisorplanta = fields.Many2one('supervisor.area', string="Supervisor cliente")
    area = fields.Char(string='Area', store=True)
    bitacorapmv = fields.Boolean(string="Bitacora PMV", default=False, help="Indica si este avance cuenta con bitacora")
    numlic = fields.Char(string='#Bitacora/Lic.', store=True)
    cot = fields.Char(string='#Cot/Presupuesto', store=True)
    
    @api.onchange('factura')
    def _onchange_factura(self):
        if self.factura:
            self.datefact = self.factura.invoice_date

    @api.depends('project_id', 'task_id')
    def _compute_name(self):
        for rec in self:
            if rec.project_id and rec.task_id:
                rec.name = f"{rec.project_id.name} - {rec.task_id.name}"
            else:
                rec.name = False

    name = fields.Char(string="Name", compute='_compute_name')

    def action_mark_invoiced(self):
        for record in self:
            record.is_invoiced = True
            record.state = 'fact'
    
    def action_mark_not_invoiced(self):
        for record in self:
            record.is_invoiced = False
            record.state = 'no_fact'

    def action_mark_incobrable(self):
        for record in self:
            record.is_invoiced = False
            record.state = 'inc'
    
    @api.depends('unit_progress')
    def _project_id(self):
        for u in self:
            u.project_id = u.env['project.project'].search([('id', '=', u.projid)], limit=1)
    
    @api.model
    def _chosen_tasks(self):
        for u in self:
            tasks = u.env['project.sub.update'].search([('update_id.id', '=', u.update_id.id)]).mapped('task_id.id')
            chosen = ""
            for i in tasks:
                chosen = chosen + str(i) + " "
            return chosen.split()
    
    @api.depends('unit_progress', 'task_id')
    def _quant_progress(self):
        for u in self:
            progress = u.task_id.quant_progress
            u.quant_progress = progress
    
    @api.depends('unit_progress', 'task_id')
    def _actual_progress(self):
        for u in self:
            if u.quant_total > 0:    
                progress = (u.unit_progress / u.quant_total) * 100
            else:
                progress = 0
            u.actual_progress = int(progress)
    
    @api.depends('unit_progress', 'task_id')
    def _total_progress(self):
        for u in self:
            if u.quant_total > 0:    
                progress = (u.virtual_quant_progress / u.quant_total) * 100
            else:
                progress = 0
            u.total_progress = int(progress)
    
    @api.depends('unit_progress', 'task_id')
    def _actual_progress_percentage(self):
        for u in self:
            u.actual_progress_percentage = u.actual_progress / 100
    
    @api.depends('unit_progress', 'task_id')
    def _total_progress_percentage(self):
        for u in self:
            u.total_progress_percentage = u.virtual_total_progress / 100
    
    @api.depends('unit_progress', 'task_id')
    def _virtual_quant_progress(self):
        for u in self:
            if not u.id:
                if not u._origin.id:
                    progress = u.task_id.quant_progress + u.unit_progress
                else:
                    self_total = u.env['project.sub.update'].search([('project_id.id', '=', u.project_id.id),
                                                 ('task_id.id', '=', u.task_id.id),
                                                 ('id', '<', u._origin.id)]).mapped('unit_progress')
                    progress = sum(self_total) + u.unit_progress
            else:
                self_total = u.env['project.sub.update'].search([('project_id.id', '=', u.project_id.id),
                                                 ('task_id.id', '=', u.task_id.id),
                                                 ('id', '<=', u.id)]).mapped('unit_progress')
                progress = sum(self_total)
            u.virtual_quant_progress = progress

    @api.depends('unit_progress', 'task_id')
    def _virtual_total_progress(self):
        for u in self:
            if u.quant_total > 0:    
                progress = (u.virtual_quant_progress / u.quant_total) * 100
            else:
                progress = 0
            u.virtual_total_progress = int(progress)
    
    @api.depends('unit_progress', 'task_id')
    def _missing_quant(self):
        for u in self:
            u.missing_quant = u.task_id.total_pieces - u.virtual_quant_progress
    
    @api.depends('unit_progress', 'task_id')
    def _sale_current(self):
        for u in self:
            u.sale_current = u.unit_progress * u.task_id.price_unit
    
    @api.depends('unit_progress', 'task_id')
    def _sale_actual(self):
        for u in self:
            u.sale_actual = u.virtual_quant_progress * u.task_id.price_unit
    
    @api.depends('unit_progress', 'task_id')
    def _sale_total(self):
        for u in self:
            u.sale_total = u.task_id.total_pieces * u.task_id.price_unit

    @api.depends('unit_progress', 'task_id')
    def _sale_missing(self):
        for u in self:
            u.sale_missing = u.sale_total - u.sale_actual

    @api.depends('unit_progress', 'task_id')
    def _sale_current_text(self):
        for u in self:
            sale = "%.2f" % u.sale_current
            value_len = sale.find('.')
            for i in range(value_len, 0, -1):
                sale = sale[:i] + ',' + sale[i:] if (value_len-i) % 3 == 0 and value_len != i else sale
            u.sale_current_text = '$' + sale

    @api.depends('unit_progress', 'task_id')
    def _sale_actual_text(self):
        for u in self:
            sale = "%.2f" % u.sale_actual
            value_len = sale.find('.')
            for i in range(value_len, 0, -1):
                sale = sale[:i] + ',' + sale[i:] if (value_len-i) % 3 == 0 and value_len != i else sale
            u.sale_actual_text = '$' + sale
    
    @api.depends('unit_progress', 'task_id')
    def _sale_total_text(self):
        for u in self:
            sale = "% .2f" % u.sale_total
            value_len = sale.find('.')
            for i in range(value_len, 0, -1):
                sale = sale[:i] + ',' + sale[i:] if (value_len-i) % 3 == 0 and value_len != i else sale
            u.sale_total_text = '$' + sale

    @api.depends('unit_progress', 'task_id')
    def _sale_missing_text(self):
        for u in self:
            sale = "% .2f" % u.sale_missing
            value_len = sale.find('.')
            for i in range(value_len, 0, -1):
                sale = sale[:i] + ',' + sale[i:] if (value_len-i) % 3 == 0 and value_len != i else sale
            u.sale_missing_text = '$' + sale
    
    @api.onchange('task_id', 'unit_progress') 
    def _task_domain(self):
        tasks = [0 for c in range(len(self.update_id.sub_update_ids))]
        task_ids = ""
        i = 0
        for u in self.update_id.sub_update_ids:
            tasks[i] = u.task_id.id
            task_ids = task_ids + str(u.task_id.id) + " "
            i = i + 1
        domain = [('project_id.id', '=', self.project_id.id), ('is_complete', '=', False), ('id', 'not in', tasks)]
        return {'domain': {'task_id': domain}}

    @api.depends('task_id')
    def _dom(self):
        tasks = [0 for c in range(len(self.update_id.sub_update_ids))]
        task_ids = ""
        i = 0
        for u in self.update_id.sub_update_ids:
            tasks[i] = u.task_id.id
            task_ids = task_ids + str(u.task_id.id) + " "
            i = i + 1
        domain = str(tasks)
        self.domain = domain
    
    @api.constrains('task_id')
    def _update_task(self):
        for u in self:
            if not u.task_id:
                raise ValidationError("Tiene que seleccionar una tarea")
    
    @api.constrains('quant_progress')
    def _update_units(self):
        for u in self:
            if u.task_id:
                if u.quant_progress > u.quant_total:
                    raise ValidationError("Sobrepasa el número de unidades pedidas")
    
    @api.constrains('unit_progress')
    def _check_units(self):
        for u in self:
            if u.task_id:
                if u.unit_progress <= 0:
                    raise ValidationError("Cantidad inválida de unidades")

    @api.constrains('item_ids')
    def _check_unique_items(self):
        for u in self:
            item_ids = u.item_ids.mapped('item_id')
            if len(item_ids) != len(set(item_ids)):
                raise ValidationError('No se pueden agregar ítems duplicados.')

    @api.constrains('sub_update_ids.task_id')
    def _check_unique_task_id(self):
        for u in self:
            task_ids = u.sub_update_ids.mapped('task_id')
            if len(task_ids) != len(set(task_ids)):
                raise ValidationError('No se pueden agregar tareas duplicadas.')

    @api.model
    def update_sale_totals(self):
        sub_updates = self.search([])
        for sub_update in sub_updates:
            if sub_update.task_id:
                sub_update.sale_total = sub_update.task_id.total_pieces * sub_update.task_id.price_unit
                sub_update.sale_current = sub_update.unit_progress * sub_update.task_id.price_unit
