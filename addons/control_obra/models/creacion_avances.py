from odoo import fields, models, api, _
from datetime import datetime, date
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class CreacionAvances(models.Model):
    _name = "creacion.avances"
    _description = "Trabajos"
    _order = "date asc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # Campo para el nombre que se mostrara en la lista de busqueda
    display_name = fields.Char(
        string="Nombre a mostrar",
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('name', 'date')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.date:
                formatted_date = record.date.strftime("%d/%m/%Y")
                record.display_name = f"{record.name} - {formatted_date}"
            else:
                record.display_name = record.name or 'Nuevo Avance'

    # Metodo para buscar con la nueva logica
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('display_name', operator, name)]

        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    # Campo para manejo de los estados del avance.
    avances_state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("confirmed", "Confirmado"),
            ("assigned", "Asignado"),
        ],
        string="Estado",
        copy=False,
        default="draft",
        tracking=True,
        compute="_compute_avances_estados",
        store=True
    )

    @api.depends('sale_order_id', 'project_id', 'task_id')
    def _compute_avances_estados(self):
        for record in self:
            # Para registros nuevos, siempre draft
            if not record.id:
                record.avances_state = 'draft'
                continue

            # Si ya tiene un estado manualmente asignado y no es draft, respetarlo
            if record.avances_state in ['confirmed', 'assigned']:
                # Solo cambiar a assigned si está confirmed y tiene los datos completos
                if (record.avances_state == 'confirmed' and
                        record.project_id and record.task_id and record.sale_order_id):
                    record.avances_state = 'assigned'
                # Mantener el estado actual en otros casos
                continue

            # Lógica automática SOLO si está en draft
            if record.avances_state == 'draft':
                if record.project_id and record.task_id and record.sale_order_id:
                    # Permanece en draft para permitir confirmación manual
                    record.avances_state = 'draft'
                else:
                    record.avances_state = 'draft'

    # Método opcional para confirmar utilizando un button desde la vista
    def action_confirmado_avances(self):
        for record in self:
            if record.avances_state == 'draft':
                # 1. Validación de campos requeridos
                record._validate_required_fields()

                # 2. Cambiar a estado confirmed
                record.avances_state = 'confirmed'
                record.message_post(body=_("El avance ha sido confirmado manualmente."))

                # 3. Si tiene todos los datos, pasar automáticamente a assigned
                if record.project_id and record.task_id and record.sale_order_id:
                    record.avances_state = 'assigned'
                    record.message_post(body=_("El avance ha sido asignado automáticamente."))

            else:
                raise UserError(_("El avance solo puede ser confirmado desde el estado 'Borrador'."))

    # Método para las validaciones 
    def _validate_required_fields(self):
        """Validación que se ejecuta al confirmar el avance"""
        required_fields = {
            'producto': 'Producto',
            'date': 'Fecha',
            'ct': 'CT (Centro de Trabajo)',
            'planta': 'Planta',
            'hora_inicio': 'Hora De Inicio',
            'hora_termino': 'Hora De Termino',
            'supervisorplanta': 'Supervisor Cliente',
            'responsible_id': 'Supervisor Interno',
            'licencia': 'Licencia/OM',
            'unit_progress': 'Avance de Unidades',
        }

        missing_fields = []
        for field_name, field_label in required_fields.items():
            if not getattr(self, field_name):
                missing_fields.append(f"- {field_label}")

        if missing_fields:
            error_message = _(
                "Antes de confirmar el avance, por favor complete los siguientes campos obligatorios:\n\n%s"
            ) % ("\n".join(missing_fields))
            raise ValidationError(error_message)

        # Validación de horas
        if self.hora_inicio and self.hora_termino and self.hora_termino <= self.hora_inicio:
            raise ValidationError(_("¡Ups! La hora de término debe ser posterior a la hora de inicio."))

    # Método opcional para revertir a borrador utilizando un button desde la vista
    def action_revert_avances_to_draft(self):
        self.ensure_one()
        if self.avances_state in ('confirmed', 'assigned'):
            self.avances_state = 'draft'
            self.message_post(body=_("El avance ha sido revertido a 'Borrador'."))
        else:
            raise UserError(_("El avance no puede ser revertido a borrador desde el estado actual."))

    # Indenficador para los avances
    name = fields.Char(
        string="ID Avance",
        copy=False,
        default=lambda self: _("Nuevo"),
        readonly=True,
        index=True,
        tracking=True,
    )

    # Método para crear y asignar la estructura al identificador
    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        date_str = now.strftime("%y%m%d%H%M%S")
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = f"{date_str}" #vals["name"] = f"AV/{date_str}"

        records = super().create(vals_list)
        # Llama a la lógica de creación de tareas después de crear los registros
        records._try_create_preliminary_task()

        return records

    # Se ejecuta cada vez que se actualiza un registro.
    def write(self, vals):
        # Primero, ejecuta la escritura normal
        res = super().write(vals)
        # Después de guardar, intenta crear la tarea PEND por si se acaban de rellenar los campos 'producto' o 'ct'.
        self._try_create_preliminary_task()
        return res

    def _try_create_preliminary_task(self):
        # Busca el proyecto PEND una sola vez para el conjunto de registros.
        proyecto_pendiente = self.env['project.project'].search([('name', 'ilike', 'PEND ORDEN DE VENTA')], limit=1)
        if not proyecto_pendiente:
            return  # Si no existe el proyecto PEND, no hacemos nada.

        # Itera sobre los avances (sea en creación o actualización)
        for record in self:
            # Condiciones para crear la tarea:
            # 1. Es preliminar (sin SO).
            # 2. Tiene producto y CT.
            # 3. Aún no tiene una tarea asignada.
            if record.is_avance_preliminar and record.producto and record.ct and not record.task_id:

                # Asigna el proyecto PEND si no lo tiene
                if not record.project_id:
                    record.project_id = proyecto_pendiente

                # Construye el nombre de la tarea y busca si ya existe
                nombre_tarea = f"PEND{record.name or 'SOV'}-{record.producto.name}-{record.ct.name}"
                tarea_existente = self.env['project.task'].search([
                    ('project_id', '=', proyecto_pendiente.id),
                    ('name', '=', nombre_tarea),
                ], limit=1)

                if tarea_existente:
                    record.task_id = tarea_existente.id
                else:
                    _logger.info(f"Creando tarea preliminar vía write/create: {nombre_tarea}")
                    nueva_tarea = self.env['project.task'].create({
                        'name': nombre_tarea,
                        'project_id': proyecto_pendiente.id,
                        'partner_id': record.cliente.id,
                        'is_control_obra': True,
                        'description': f"Creada automáticamente desde el avance {record.name}. Cliente: {record.cliente.name}.",
                    })
                    record.task_id = nueva_tarea.id

                    # Registrar mensaje en el Chatter de la tarea
                    nueva_tarea.message_post(
                        body=_("📋 **Creada automáticamente desde el avance:** %s<br/>"
                               "• Producto: %s<br/>"
                               "• Centro de Trabajo: %s<br/>"
                               "• Cliente: %s<br/>"
                               "• Proyecto: PEND ORDEN DE VENTA") % (
                               record.name,
                               record.producto.name,
                               record.ct.name,
                               record.cliente.name if record.cliente else 'N/A',
                        ),
                        subject="Creación automática desde avance"
                    )

                    _logger.info(f"Tarea preliminar creada: {nueva_tarea.name} para el avance {record.name}")

    # Método migracion compras, gastos, etc.
    def _migrate_related_records(self, old_task_id, new_task_id):
        if not old_task_id:
            return

        # 1. Migración (hr.expense)
        expenses_to_migrate = self.env['hr.expense'].search([('task_id', '=', old_task_id)])
        if expenses_to_migrate:
            expenses_to_migrate.write({'task_id': new_task_id})
            _logger.info(f"Migrado {old_task_id} para {new_task_id}")
            _logger.info(
                f"Migrado: {len(expenses_to_migrate)} expenses from Task ID {old_task_id} to Task ID {new_task_id}.")

        # 2. Migración (purchase.order)
        purchases_lines_to_migrate = self.env['purchase.order.line'].search([('task_id', '=', old_task_id)])
        if purchases_lines_to_migrate:
            purchases_lines_to_migrate.write({'task_id': new_task_id})
            _logger.info(
                f"Migrado {len(purchases_lines_to_migrate)} purchases from Task ID{old_task_id} to Task ID {new_task_id}.")

    # Campo para saber quien creo el avance.
    created_by = fields.Many2one(
        comodel_name="res.users",
        string="Capturado Por",
        default=lambda self: self.env.user,
        readonly=True,
        tracking=2,
    )

    is_avance_preliminar = fields.Boolean(
        string="Avance Preliminar",
        tracking=True,
        help="Indica si el avance esta sin ser asignado a una orden de venta",
        compute="_compute_avances_preliminar",
        store=True,
    )

    @api.depends("sale_order_id")
    def _compute_avances_preliminar(self):
        for record in self:
            record.is_avance_preliminar = not record.sale_order_id

    is_transferible = fields.Boolean(
        string="Transferible",
        compute="_compute_avances_transferible",
        store=True,
        help="Indica si el avance puede ser transferido a un proyecto con orden de venta"
    )

    @api.depends("avances_state", "is_avance_preliminar", "project_id")
    def _compute_avances_transferible(self):
        for record in self:
            record.is_transferible = (
                    record.avances_state == 'confirmed' and
                    record.is_avance_preliminar and
                    record.project_id and
                    'PEND' in record.project_id.name
            )

    # Bandera para asignar avance a un proyecto desde la edicion del avance
    asignar_avance = fields.Boolean(
        string="Asignar Avance",
        default=False,
    )

    # Metodo para cambiar el estado
    def toggle_asignar_avance(self):
        for record in self:
            record.asignar_avance = not record.asignar_avance
            return True

    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string="Línea de Venta",
        related='task_id.sale_line_id',
        store=True,
    )

    partida_linea = fields.Char(
        related="sale_order_line_id.partida",
        string="Partida"
    )

    dashboard_task_id = fields.Many2one(
        "task.update",
        string="Dashboard Task",
    )

    ############################################################
    # SECCION PRINCIPAL DEL FORMATO DEL AVANCE: DATOS INTERNOS #
    ############################################################
    # Campo que hacer referencia con la orden de venta relacionada al proyecto.
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Orden De Venta",
        related="task_id.sale_order_id",  # project_id.reinvoiced_sale_order_id
        help="Orden De Venta Relacionada Al Trabajo",
        tracking=True,
    )
    # Campo que hace referencia a las especialidades de la orden de venta.
    especialidad = fields.Many2many(
        "crm.tag",
        string="Especialidad",
        related="sale_order_id.tag_ids",
        help="Especialidad de la Orden De Venta",
    )

    # Campo para mostrar a que proyecto se encuentra enlazado el avance.
    project_id = fields.Many2one(
        "project.project",
        string="Proyecto",
        domain="[('is_proyecto_obra', '=', True)]",
        help="Proyecto a cual el avance esta asignado.",
        tracking=True,
    )

    # Método para rellenar el campo project_id en base a la actualización.
    @api.onchange("update_id")
    def _onchange_update_id(self):
        if self.update_id and self.update_id.project_id:
            self.project_id = self.update_id.project_id

    # Método para manejar la transicion de los proyectos
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Cuando se cambia el proyecto, resetear la tarea si viene de PEND"""
        for record in self:
            if record.project_id and record.task_id:
                # Si el proyecto anterior era PEND y el nuevo no, resetear la tarea
                old_project = self.env['project.project'].browse(self._origin.project_id.id) if self._origin else False
                if old_project and 'PEND' in old_project.name and 'PEND' not in record.project_id.name:
                    record.task_id = False

    # Campo para visualizar a que actufalización se asigno el avance.
    update_id = fields.Many2one(
        "project.update",
        string="Actualización",
        ondelete="cascade",
        help="Actualización a cual el avance esta asignado.",
        tracking=True,
    )

    # Campo para obtener la última actualización del proyecto al cual se asignara el avance
    ultima_actualizacion = fields.Char(
        string="Ultima Actualización",
        compute="_ultima_actualizacion",
        store=False,
    )

    @api.depends("project_id")
    def _ultima_actualizacion(self):
        for record in self:
            # Buscar el último registro de 'project_update' para el proyecto
            last_update = self.env['project.update'].search([
                ('project_id', '=', record.project_id.id)
            ], order='create_date desc', limit=1)

            if last_update:
                record.ultima_actualizacion = last_update.name
            else:
                record.ultima_actualizacion = "No hay actualizaciones previas."

    # Campo para visualizar con qué tarea se agregó el avance.
    task_id = fields.Many2one(
        "project.task",
        string="Tarea",
        help="Tarea Del Proyecto (Aqui Vera La Tarea En La Cual El Avance Estara Relacionado)",
        tracking=True,
        domain="[('project_id', '=', project_id), ('state', 'not in', ['1_canceled', '1_done'])]" #('stage_id', 'not in', [30])
    )

    # Campo visualizar el cliente.
    cliente_project = fields.Many2one(
        'res.partner',
        string="Cliente",
        related="sale_order_id.partner_id",
        help="Cliente Al Cual Se Le Va A Proveer El Trabajo",
        tracking=True,
    )

    # Campo para visualizar el gerente del proyecto.
    gerente_project = fields.Many2one(
        'res.users',
        related="project_id.user_id",
        string="Gerente Proyecto",
        tracking=True,
        help="Este campo mostrara el Gerente Proyecto",
    )

    coordinador_project = fields.Many2one(
        "hr.employee",
        related="project_id.coordinador",
        string="Coordinador",
        tracking=True,
    )

    supervisor_project = fields.Many2one(
        "hr.employee",
        related="project_id.supervisor",
        string="Supervisor",
        tracking=True,
    )

    # Notas
    notas = fields.Char(
        string="Notas",
        help="Comentarios Pertinentes",
    )
    ############################################################
    #                SECCION DATOS DEL PRODUCTO                #
    ############################################################
    # Campo con relación al producto.
    producto = fields.Many2one(
        "product.product",
        string="Producto",
        help="Producto/Servicio A Trabajar",
        tracking=True,
        domain="[('sale_ok', '=', True),('type', '=', 'service')]",
    )

    # Campo relacionado con la especialidad del producto.
    especialidad_producto = fields.Many2one(
        string="Especialidad del Servicio",
        related="producto.categ_id",
        help="Especialidad Del Producto",
        tracking=True,
    )

    # Campo relacionado a la unidad de medida del producto.
    unidad_medida = fields.Many2one(
        string="Unidad",
        related="producto.uom_id",
        help="Unidad En La Que Se Mide Producto Ejemplo: Lote, Pza.",
        tracking=True,
    )

    # Campo relacionado al precio por unidad del producto.
    precio_unidad = fields.Float(
        related="producto.list_price",
        string="Precio Unitario",
        help="Precio Unitario Del Producto (Este Precio Es Sin IVA)",
        tracking=True,
    )

    ############################################################
    #               DATOS GENERALES DEL TRABAJO                #
    ############################################################
    # Campo que hace referencia al nombre de la orden de venta que a la vez es el nombre del proyecto.
    oc_pedido = fields.Char(
        string="OC/Pedido",
        related="project_id.name",
        help="Orden De Venta (Este Campo Depende Directamente De Tener Una Orden De Venta)",
        tracking=True,
    )
    # Campo fecha que hace referencia a la fecha de reporte del avance
    date = fields.Date(
        string="Fecha",
        help="Fecha En Que Se Realizo El Trabajo",
        tracking=True,
    )

    # Método para obtener la fecha del día y agregar el campo Date
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res["date"] = date.today()
        return res

    # Campo que hace referencia al centro de trabajo del avance.
    ct = fields.Many2one(
        "control.centro.trabajo",
        string="CT",
        help="Centro De Trabajo Donde Se Esta Realizando El Trabajo",
        tracking=True,
    )
    # Campo que se ocupa para poder guardar el cliente del ct (Centro de Trabajo) Utilizado para Metodos No Impacta en la vista.
    cliente = fields.Many2one(
        "res.partner",
        string="Cliente del Centro De Trabajo",
        compute="_compute_cliente",
        store=True,
        tracking=True,
    )

    # Metodo para sacar el cliente de ct y asignarlo al campo cliente.
    @api.depends("ct")
    def _compute_cliente(self):
        for record in self:
            if record.ct and record.ct.cliente:
                record.cliente = record.ct.cliente
            else:
                record.cliente = False

    # Metodo para validación de Cliente CT corresponda con Cliente Planta, Area, Supervisor Cliente
    planta_domain = fields.Char(compute="_compute_domains", store=True)
    supervisor_domain = fields.Char(compute="_compute_domains", store=True)

    # Metodo para asignar los dominios a los campos, planta y supervisor cliente
    @api.depends("ct.cliente")
    def _compute_domains(self):
        for record in self:
            if record.ct and record.ct.cliente:
                # Dominio para Planta: Se usa el campo 'cliente' que asume que existe en el modelo 'planta.avance'
                planta_domain_list = [("cliente", "=", record.ct.cliente.id)]

                # Dominio para Supervisor: Se usa el campo 'parent_id' estándar de Odoo
                # para filtrar contactos por su empresa.
                supervisor_domain_list = [("parent_id", "=", record.ct.cliente.id),
                                          ("tipo_contacto", "=", 'Supervisor')]

                planta_domain_str = str(planta_domain_list)
                supervisor_domain_str = str(supervisor_domain_list)
            else:
                planta_domain_str = str([("id", "=", False)])
                supervisor_domain_str = str([("id", "=", False)])

            record.planta_domain = planta_domain_str
            record.supervisor_domain = supervisor_domain_str

            # Limpieza de campos si no coinciden
            if record.planta and record.planta.cliente != record.ct.cliente:
                record.planta = False

            # Validación correcta para el supervisor
            # Se compara el 'parent_id' del supervisor con el cliente
            if (
                    record.supervisorplanta
                    and record.supervisorplanta.parent_id != record.ct.cliente
            ):
                record.supervisorplanta = False

    # Campo para ?.
    or_rfq = fields.Char(
        string="OR/RFQ",
        help="Cotizaciónes",
        tracking=True,
    )

    # Campo para agregar el número de cotización del avance o servicio a realizar/reportar.
    no_cotizacion = fields.Char(
        string="No. Cotización",
        tracking=True,
    )

    # Campo que muestra la especialidad del trabajo que se esta haciendo.
    especialidad_trabajo = fields.Many2one(
        string="Especialidad De Trabajo",
        related="task_id.disc",
        help="Especialidad Del Trabajo (Este Dependera Directamente De La Etiquetas En La Orden De Venta)",
        tracking=True,
    )

    ############################################################
    #            DESCRIPCIÓN DETALLADA DEL TRABAJO             #
    ############################################################
    # Campo que describe la planta donde se realizo el trabajo del avance presentado.
    planta = fields.Many2one(
        "control.planta",
        string="Planta",
        help="Planta en la que se realiza el trabajo.",
        tracking=True,
    )

    # Campo para asignar el area exacta donde se realizo el servicio o se esta realizando.
    area_equipo = fields.Char(
        string="Area Trabajo Y/O Tag. Equipo",
        help="Area Y/O equipo donde se realiza el trabajo.",
        tracking=True,
    )

    # Campo con la hora de inicio reportada de la realizacion del trabajo/servicio que reporta el avance
    hora_inicio = fields.Float(
        string="Hora De Inicio",
        help="Hora Inicio Del Trabajo",
        tracking=True,
    )

    # Campo con la hora de termino reportada de la realizacion del trabajo/servicio que reporta el avance
    hora_termino = fields.Float(
        string="Hora De Termino",
        help="Hora Termino Del Trabajo",
        tracking=True,
    )

    # Campo para asignar el responsable de supervisar el servicio por parte del cliente.
    supervisorplanta = fields.Many2one(
        "res.partner",
        string="Supervisor Cliente",
        help="Supervisor Del Trabajo Por Parte Del Cliente",
        tracking=True,
    )

    # Campo para asignar el responsable del servicio a realizar por parte interna (AYASA).
    responsible_id = fields.Many2one(
        "hr.employee",
        string="Supervisor Interno",
        domain="[('supervisa', '=', True)]",
        help="Supervisor Del Trabajo Interno (AYASA)",
        tracking=True,
    )

    licencia = fields.Char(
        string="Licencia/OM",
        size=20,  # 8
        help="Licencia Proporcionado Por El Cliente/Planta Para Poder Realizar El Trabajo",
        tracking=True,
    )

    ############################################################
    #                      AVANCES ACTUAL                      #
    ############################################################
    # Avance Actual
    unit_progress = fields.Float(string="Avance de Unidades", default=0.0)
    actual_progress_percentage = fields.Float(
        compute="_actual_progress_percentage", string="Avance Porcentual", default=0.0
    )
    virtual_quant_progress = fields.Float(
        string="Unidades Entregadas (virtual)",
        compute="_virtual_quant_progress",
        store=True,
        default=0.0,
    )
    missing_quant = fields.Float(string="Unidades Faltantes", compute="_missing_quant")

    # Avance del Servicio
    quant_total = fields.Float(related="task_id.total_pieces")
    sale_current = fields.Float(
        string="Avance Del Subtotal", compute="_sale_current", store=True
    )
    virtual_total_progress = fields.Integer(
        string="Progreso Total (virtual)", compute="_virtual_total_progress", default=0
    )

    # Campo para manejar el costo del avance antes de ser asignado a un proyecto.
    costo_avance = fields.Float(
        string="Costo Del Avance",
        tracking=True,
        help="Costo Total Del Avance (Este Costo Es Representado Por El Valor Unitario Del Producto X El Total De Unidades Entregadas)",
        compute="compute_costo_avance",
    )

    # Metodo para calcular el valor del avance antes de ser asignado a un proyecto/orden de venta
    @api.depends('precio_unidad', 'unit_progress')
    def compute_costo_avance(self):
        for record in self:
            record.costo_avance = record.precio_unidad * record.unit_progress

    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        # Relaciona la moneda con la de la orden de venta, o usa la de la compañía por defecto
        related='sale_order_id.currency_id',
        store=True,
        help="La moneda del avance, tomada de la orden de venta.",
    )

    costo_avance_formateado = fields.Char(
        compute="_compute_costo_formateado",
        string="Costo Del Avance Formateado",
        store=True,
    )

    # Metodo para el formateado del campo costo avance
    @api.depends('costo_avance')
    def _compute_costo_formateado(self):
        for record in self:
            record.costo_avance_formateado = "${:,.2f}".format(record.costo_avance)

    bitacorapmv = fields.Boolean(
        string="Bitacora PMV",
        default=False,
        help="Indica si este avance cuenta con bitacora",
    )
    om = fields.Char(string="# OM")
    numlic = fields.Char(string="#Bitacora/Lic.", store=True, size=20)
    cot = fields.Char(string="#Cot/Presupuesto", store=True)
    estimado = fields.Boolean(
        string="Estimado",
        default=False,
        help="Indica si este avance ya ha sido estimado",
    )
    avanceparc = fields.Char(string="Avance Parcial")
    datefact = fields.Date(string="Fecha De Factura", store=True)
    factura = fields.Many2one(
        "account.move",
        string="Factura",
        domain="[('state', '=', 'posted'), ('move_type', '=', 'out_invoice')]",
    )
    sale_total = fields.Float(
        string="Subtotal De La Venta", compute="_sale_total", store=True
    )
    sale_actual = fields.Float(
        string="Subtotal Entregado", compute="_sale_actual", store=True
    )
    sale_missing = fields.Float(
        string="Subtotal Faltante", compute="_sale_missing", store=True
    )

    proj = fields.Many2one(related="update_id.project_id")
    projid = fields.Integer(related="proj.id", string="ID Del Proyecto")
    projname = fields.Char(
        related="proj.name", string="Nombre Del Proyecto",
    )
    prev_progress = fields.Integer(
        related="task_id.progress", string="Current Progress",
    )
    quant_progress = fields.Float(
        string="Unidades Entregadas", compute="_quant_progress", store=True, default=0.0
    )
    actual_progress = fields.Integer(
        compute="_actual_progress", string="Avance", default=0
    )
    total_progress = fields.Integer(
        string="Progreso Total", compute="_total_progress", store=True, default=0
    )
    total_progress_percentage = fields.Float(compute="_total_progress_percentage")

    # Text
    sale_current_text = fields.Char(
        string="Avance Del subtotal (pesos)", compute="_sale_current_text", store=True
    )
    sale_actual_text = fields.Char(
        string="Subtotal Entregado (pesos)", compute="_sale_actual_text", store=True
    )
    sale_total_text = fields.Char(
        string="Subtotal De La Venta (pesos)", compute="_sale_total_text", store=True
    )
    sale_missing_text = fields.Char(
        string="Subtotal Faltante (pesos)", compute="_sale_missing_text", store=True
    )

    task_name = fields.Char(related="task_id.name", string="Nombre De La Tarea")
    domain = fields.Char(string="Dominio", compute="_dom")
    color = fields.Integer(related="update_id.color", string="Color")
    estado = fields.Selection(related="update_id.status", string="Estado Tarea")

    invoiced = fields.Float(string="Facturado", related="task_id.invoiced", store=True)
    is_invoiced = fields.Boolean(
        string="¿Avance Facturado?",
        default=False,
        help="Indica si este avance ya ha sido facturado",
    )
    cotizacion = fields.Char(string="# Cotización")

    @api.onchange("factura")
    def _onchange_factura(self):
        if self.factura:
            self.datefact = self.factura.invoice_date

    def action_mark_invoiced(self):
        for record in self:
            record.is_invoiced = True
            record.state = "fact"

    def action_mark_not_invoiced(self):
        for record in self:
            record.is_invoiced = False
            record.state = "no_fact"

    def action_mark_incobrable(self):
        for record in self:
            record.is_invoiced = False
            record.state = "inc"

    @api.depends("unit_progress")
    def _project_id(self):
        for u in self:
            u.project_id = u.env["project.project"].search(
                [("id", "=", u.projid)], limit=1
            )

    @api.model
    def _chosen_tasks(self):
        for u in self:
            tasks = (
                u.env["creacion.avances"]
                .search([("update_id.id", "=", u.update_id.id)])
                .mapped("task_id.id")
            )
            chosen = ""
            for i in tasks:
                chosen = chosen + str(i) + " "
            return chosen.split()

    @api.depends("unit_progress", "task_id")
    def _quant_progress(self):
        for u in self:
            progress = u.task_id.quant_progress
            u.quant_progress = progress

    @api.depends("unit_progress", "task_id")
    def _actual_progress(self):
        for u in self:
            if u.quant_total > 0:
                progress = (u.unit_progress / u.quant_total) * 100
            else:
                progress = 0
            u.actual_progress = int(progress)

    @api.depends("unit_progress", "task_id")
    def _total_progress(self):
        for u in self:
            if u.quant_total > 0:
                progress = (u.virtual_quant_progress / u.quant_total) * 100
            else:
                progress = 0
            u.total_progress = int(progress)

    @api.depends("unit_progress", "task_id")
    def _actual_progress_percentage(self):
        for u in self:
            u.actual_progress_percentage = u.actual_progress / 100

    @api.depends("unit_progress", "task_id")
    def _total_progress_percentage(self):
        for u in self:
            u.total_progress_percentage = u.virtual_total_progress / 100

    @api.depends("unit_progress", "task_id")
    def _virtual_quant_progress(self):
        for u in self:
            if not u.id:
                if not u._origin.id:
                    progress = u.task_id.quant_progress + u.unit_progress
                else:
                    self_total = (
                        u.env["creacion.avances"]
                        .search(
                            [
                                ("project_id.id", "=", u.project_id.id),
                                ("task_id.id", "=", u.task_id.id),
                                ("id", "<", u._origin.id),
                            ]
                        )
                        .mapped("unit_progress")
                    )
                    progress = sum(self_total) + u.unit_progress
            else:
                self_total = (
                    u.env["creacion.avances"]
                    .search(
                        [
                            ("project_id.id", "=", u.project_id.id),
                            ("task_id.id", "=", u.task_id.id),
                            ("id", "<=", u.id),
                        ]
                    )
                    .mapped("unit_progress")
                )
                progress = sum(self_total)
            u.virtual_quant_progress = progress

    @api.depends("unit_progress", "task_id")
    def _virtual_total_progress(self):
        for u in self:
            if u.quant_total > 0:
                progress = (u.virtual_quant_progress / u.quant_total) * 100
            else:
                progress = 0
            u.virtual_total_progress = int(progress)

    @api.depends("unit_progress", "task_id")
    def _missing_quant(self):
        for u in self:
            u.missing_quant = u.task_id.total_pieces - u.virtual_quant_progress

    @api.depends("unit_progress", "task_id")
    def _sale_current(self):
        for u in self:
            u.sale_current = u.unit_progress * u.task_id.price_unit

    @api.depends("unit_progress", "task_id")
    def _sale_actual(self):
        for u in self:
            u.sale_actual = u.virtual_quant_progress * u.task_id.price_unit

    # Campo A Modificar
    @api.depends("unit_progress", "task_id")
    def _sale_total(self):
        for u in self:
            u.sale_total = u.task_id.total_pieces * u.task_id.price_unit

    @api.depends("unit_progress", "task_id")
    def _sale_missing(self):
        for u in self:
            u.sale_missing = u.sale_total - u.sale_actual

    @api.depends("unit_progress", "task_id")
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

    @api.depends("unit_progress", "task_id")
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

    @api.depends("unit_progress", "task_id")
    def _sale_total_text(self):
        for u in self:
            sale = "% .2f" % u.sale_total
            value_len = sale.find(".")
            for i in range(value_len, 0, -1):
                sale = (
                    sale[:i] + "," + sale[i:]
                    if (value_len - i) % 3 == 0 and value_len != i
                    else sale
                )
            u.sale_total_text = "$" + sale

    @api.depends("unit_progress", "task_id")
    def _sale_missing_text(self):
        for u in self:
            sale = "% .2f" % u.sale_missing
            value_len = sale.find(".")
            for i in range(value_len, 0, -1):
                sale = (
                    sale[:i] + "," + sale[i:]
                    if (value_len - i) % 3 == 0 and value_len != i
                    else sale
                )
            u.sale_missing_text = "$" + sale

    @api.onchange("task_id", "unit_progress")
    def _task_domain(self):
        tasks = [0 for c in range(len(self.update_id.sub_update_ids))]
        task_ids = ""
        i = 0
        for u in self.update_id.sub_update_ids:
            tasks[i] = u.task_id.id
            task_ids = task_ids + str(u.task_id.id) + " "
            i = i + 1
        domain = [
            ("project_id.id", "=", self.project_id.id),
            ("is_complete", "=", False),
            ("id", "not in", tasks),
        ]
        return {"domain": {"task_id": domain}}

    @api.depends("task_id")
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

    # Este metodo de validación fue modificado.
    @api.constrains("quant_progress", "task_id")
    def _update_units(self):
        for u in self:
            if u.task_id and u.task_id.total_pieces > 0:
                other_sub_updates = self.env['creacion.avances'].search([
                    ('task_id', '=', u.task_id.id),
                    ('id', '!=', u.id)  # Excluye el registro actual para no doble-contar su valor
                ])
                sum_of_other_advances = sum(other_sub_updates.mapped('unit_progress'))
                # Calcular el nuevo progreso total acumulado para la tarea
                new_total_task_progress = sum_of_other_advances + u.unit_progress
                # Realizar la validación
                if new_total_task_progress > u.task_id.total_pieces:
                    raise ValidationError("El progreso acumulado de la tarea sobrepasa el número de unidades pedidas.")

    @api.constrains("unit_progress")
    def _check_units(self):
        for u in self:
            if u.task_id:
                if u.unit_progress <= 0:
                    raise ValidationError("Cantidad inválida de unidades")

    """
    @api.constrains("item_ids")
    def _check_unique_items(self):
        for u in self:
            item_ids = u.item_ids.mapped("item_id")
            if len(item_ids) != len(set(item_ids)):
                raise ValidationError("No se pueden agregar ítems duplicados.")

    @api.constrains("sub_update_ids.task_id")
    def _check_unique_task_id(self):
        for u in self:
            task_ids = u.sub_update_ids.mapped("task_id")
            if len(task_ids) != len(set(task_ids)):
                raise ValidationError("No se pueden agregar tareas duplicadas.")
    """

    @api.model
    def update_sale_totals(self):
        sub_updates = self.search([])
        for sub_update in sub_updates:
            if sub_update.task_id:
                sub_update.sale_total = (
                        sub_update.task_id.total_pieces * sub_update.task_id.price_unit
                )
                sub_update.sale_current = (
                        sub_update.unit_progress * sub_update.task_id.price_unit
                )

    # Pruebas
    def action_unlink_from_update(self):
        """
        Desvincula un avance de su actualización y proyecto, regresándolo
        al estado 'Confirmado' para que pueda ser reasignado.
        Cuando se llama desde un botón en una línea, 'self' es solo ese registro.
        """
        self.ensure_one()  # Aseguramos que solo se ejecute para un registro a la vez

        # Verificación de seguridad
        if self.avances_state != 'assigned':
            raise UserError(_("Solo se pueden desvincular avances que ya han sido asignados."))

        original_update_name = self.update_id.name if self.update_id else "N/A"
        original_task_name = self.task_id.name if self.task_id else "N/A"

        _logger.info(f"Iniciando desvinculación para el avance: {self.name}")

        # Limpiar los campos de vinculación y regresar el estado
        self.write({
            'update_id': False,
            'project_id': False,
            'task_id': False,
            'avances_state': 'confirmed'
        })

        # Registrar en el chatter para trazabilidad
        msg = _(
            "Avance desvinculado de la Actualización '%s' y Tarea '%s'. Ahora está disponible para ser reasignado.") % (
                  original_update_name, original_task_name)
        self.message_post(body=msg)

        _logger.info(f"Avance {self.name} desvinculado exitosamente.")

        # Simplemente retorna True, la vista se refrescará automáticamente
        return True

    # Método nuevo que permite asignar un producto si creamos el trabajo (Avance) desde la actualización del proyecto
    @api.onchange('task_id')
    def _onchange_task_project_update_set_product(self):
        # Comprobamos si se a seleccionado una tarea y si esa tarea se encuentra vinculada a una línea de orden de venta
        if self.task_id and self.task_id.sale_line_id:
            # Asigna el producto relacionado con la línea de orden de venta al campo producto del trabajo (avance)
            self.producto = self.task_id.sale_line_id.product_id
        else:
            self.producto = False

    @api.onchange('update_id', 'task_id')
    def _onchange_project_link(self):
        """Rellenamos el campo project_id basado en el avance general (update_id) o la tarea (task_id)

        Prioridad:
        1. Si existe task_id, usa su proyecto.
        2. Si no hay task_id pero si update_id, usa el proyecto del avance general.
        """

        if self.task_id:
            # Prioridad 1.
            self.project_id = self.task_id.project_id

        elif self.update_id and self.update_id.project_id:
            # Prioridad 2.
            self.project_id = self.update_id.project_id

        else:
            # Si no se tiene ninguno de los dos campos, se borra el proyecto actual
            self.project_id = False