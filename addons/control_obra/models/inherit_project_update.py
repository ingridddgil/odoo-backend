from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class InheritProjectUpdate(models.Model):
    _inherit = "project.update"
    _order = "date desc"

    #Campo Para Crear Nuevos Avances Si Desde Un Principio Se Tiene Una Orden De Venta
    sub_update_ids = fields.One2many(
        "creacion.avances", "update_id", string="Creación De Trabajos"
    )

    # Campo computado que mostrará la suma de los porcentajes de los avances asociados.
    progress_percentage = fields.Float(
        string="Porcentaje de Avance",
        compute="_compute_progress_percentage",
        store=True,
    )

    @api.depends('sub_update_ids.total_progress_percentage')
    def _compute_progress_percentage(self):
        """
        Calcula el porcentaje total de avance para esta actualización,
        sumando los porcentajes de todos los avances que contiene.
        """
        for update in self:
            # Suma los valores del campo 'total_progress_percentage' de todos
            # los registros en la lista 'sub_update_ids'.
            total_percentage = sum(update.sub_update_ids.mapped('total_progress_percentage'))
            update.progress_percentage = total_percentage

    def action_add_sub_updates(self):
        self.ensure_one()

        update = self.env["project.update"].search(
            [("project_id", "=", self.project_id.id)], order="create_date desc", limit=1
        )

        if not update:
            update = self.env["project.update"].create(
                {
                    "project_id": self.project_id.id,
                }
            )

        for sub in self.sub_update_ids:
            sub.update_id = update.id
            sub.project_id = self.project_id.id
            sub._compute_avances_estados()

            # Buscar tarea en base al nombre del producto
            if not sub.task_id and sub.producto:
                task = self.env["project.task"].search(
                    [
                        ("name", "=", sub.producto.name),
                        ("project_id", "=", sub.project_id.id),
                    ],
                    limit=1,
                )
                if task:
                    sub.task_id = task.id

        return {"type": "ir.actions.act_window_close"}

    sale_current = fields.Float(
        string="Avance del subtotal", compute="_sale_current", store=True, default=0.0
    )
    sale_actual = fields.Float(
        string="Subtotal entregado", compute="_sale_actual", store=True, default=0.0
    )
    sale_total = fields.Float(
        string="Subtotal de la venta", compute="_sale_total", store=True, default=0.0
    )
    sale_missing = fields.Float(
        string="Subtotal faltante", compute="_sale_missing", store=True, default=0.0
    )

    sale_current_text = fields.Char(
        string="Avance del subtotal (pesos)", compute="_sale_current_text", store=True
    )
    sale_actual_text = fields.Char(
        string="Subtotal entregado (pesos)", compute="_sale_actual_text", store=True
    )
    sale_total_text = fields.Char(
        string="Subtotal de la venta (pesos)", compute="_sale_total_text", store=True
    )
    sale_missing_text = fields.Char(
        string="Subtotal faltante (pesos)", compute="_sale_missing_text", store=True
    )

    @api.depends(
        "sub_update_ids", "sub_update_ids.unit_progress", "sub_update_ids.task_id"
    )
    def _sale_current(self):
        for u in self:
            sale = (
                u.env["creacion.avances"]
                .search([("update_id.id", "=", u._origin.id)])
                .mapped("sale_current")
            )
            u.sale_current = sum(sale)

    @api.depends(
        "sub_update_ids", "sub_update_ids.unit_progress", "sub_update_ids.task_id"
    )
    def _sale_actual(self):
        for u in self:
            sale = (
                u.env["project.update"]
                .search(
                    [
                        ("project_id.id", "=", u.project_id.id),
                        ("id", "<=", u._origin.id),
                    ]
                )
                .mapped("sale_current")
            )
            u.sale_actual = sum(sale)

    @api.depends(
        "sub_update_ids", "sub_update_ids.unit_progress", "sub_update_ids.task_id"
    )
    def _sale_total(self):
        for u in self:
            sale = (
                u.env["project.task"]
                .search([("project_id.id", "=", u.project_id.id)])
                .mapped("price_subtotal")
            )
            u.sale_total = sum(sale)

    @api.depends(
        "sub_update_ids", "sub_update_ids.unit_progress", "sub_update_ids.task_id"
    )
    def _sale_missing(self):
        for u in self:
            sale = u.sale_total - u.sale_actual
            u.sale_missing = sale

    @api.depends(
        "sub_update_ids", "sub_update_ids.unit_progress", "sub_update_ids.task_id"
    )
    def _sale_current_text(self):
        for u in self:
            sale = "%.2f" % u.sale_current
            value_len = sale.find(".")
            for i in range(value_len, 0, -1):
                sale = (
                    sale[:i] + "," + sale[i:]
                    if (value_len - i) % 3 == 0 and value_len != i
                    else sale
                )
            u.sale_current_text = "$" + sale

    @api.depends(
        "sub_update_ids", "sub_update_ids.unit_progress", "sub_update_ids.task_id"
    )
    def _sale_actual_text(self):
        for u in self:
            sale = "%.2f" % u.sale_actual
            value_len = sale.find(".")
            for i in range(value_len, 0, -1):
                sale = (
                    sale[:i] + "," + sale[i:]
                    if (value_len - i) % 3 == 0 and value_len != i
                    else sale
                )
            u.sale_actual_text = "$" + sale

    @api.depends(
        "sub_update_ids", "sub_update_ids.unit_progress", "sub_update_ids.task_id"
    )
    def _sale_total_text(self):
        for u in self:
            sale = "%.2f" % u.sale_total
            value_len = sale.find(".")
            for i in range(value_len, 0, -1):
                sale = (
                    sale[:i] + "," + sale[i:]
                    if (value_len - i) % 3 == 0 and value_len != i
                    else sale
                )
            u.sale_total_text = "$" + sale

    @api.depends(
        "sub_update_ids", "sub_update_ids.unit_progress", "sub_update_ids.task_id"
    )
    def _sale_missing_text(self):
        for u in self:
            sale = "%.2f" % u.sale_missing
            value_len = sale.find(".")
            for i in range(value_len, 0, -1):
                sale = (
                    sale[:i] + "," + sale[i:]
                    if (value_len - i) % 3 == 0 and value_len != i
                    else sale
                )
            u.sale_missing_text = "$" + sale

    def write(self, vals):
        if self.env.context.get('wizard_assigning'):
            return super().write(vals)

        # La validación se ejecuta ANTES de llamar a super()
        if "sub_update_ids" in vals:
            for command in vals.get('sub_update_ids'):
                # Validar solo al crear una nueva línea (comando 0)
                if command[0] == 0:
                    values = command[2]
                    
                    required_fields = {
                        # Odoo usa '_id' en los 'vals' para campos Many2one
                        'producto_id': 'Producto', 'date': 'Fecha',
                        'ct_id': 'CT (Centro de Trabajo)', 'planta_id': 'Planta',
                        'hora_inicio': 'Hora De Inicio', 'hora_termino': 'Hora De Termino',
                        'supervisorplanta_id': 'Supervisor Cliente', 'responsible_id': 'Supervisor Interno',
                        'licencia': 'Licencia/OM', 'unit_progress': 'Avance de Unidades',
                    }

                    missing_fields = [f"- {label}" for field, label in required_fields.items() if not values.get(field)]
                    
                    if missing_fields:
                        error_message = _("Para el nuevo trabajo a crear, por favor complete los siguientes campos obligatorios:\n\n%s") % ("\n".join(missing_fields))
                        raise UserError(error_message)

                    hora_inicio = values.get('hora_inicio')
                    hora_termino = values.get('hora_termino')
                    if hora_inicio is not None and hora_termino is not None and hora_termino <= hora_inicio:
                        raise UserError(_("¡Ups! La hora de término debe ser posterior a la hora de inicio."))

        # Si todas las validaciones pasan, se procede con el guardado normal.
        res = super().write(vals)

        # Tu lógica posterior para enlazar registros se mantiene igual
        if "sub_update_ids" in vals:
            for update in self:
                for sub in update.sub_update_ids:
                    if not sub.update_id:
                        sub.update_id = update.id
                    if not sub.project_id:
                        sub.project_id = update.project_id.id
                    sub._compute_avances_estados()
        return res