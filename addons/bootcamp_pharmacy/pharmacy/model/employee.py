from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError

class Employee(models.Model):
    _name = 'pharmacy.employee'
    _description = 'Pharmacy´s employee'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    PROFESSIONAL_DEGREES = ['bachelor', 'master', 'doctorate']

    id = fields.Integer(
        string = 'ID',
        require = True
    )

    name = fields.Char(
        string = 'Name',
        require =  True,
        tracking = True
    )
    occupation = fields.Char(
        string = 'Occupation',
        require = True
    )
    birthdate = fields.Date(
        string = 'Birthdate',
        require = True,
        tracking = True
    )
    age = fields.Integer(
        string = "Age",
        compute = "compute_age"
    )
    gender = fields.Selection(
        [
            ("female", "Female"),
            ("male", "Male"),
        ]
    )
    activity = fields.Boolean(
        string="Active",
        default=True
    )
    sale_order_id = fields.One2many(
        comodel_name='sale.order',
        inverse_name='id',
        string = 'Sale order'
    )
    degree = fields.Selection(
        [
            ('high_school', 'High School'),
            ('bachelor', 'Bachelor'),
            ('master', 'Master'),
            ('doctorate', 'Doctorate'),
        ],
        string='Education level',
        required=True
    )
    professional_license = fields.Char(
        string='Professional License',
        required=False
    )

    @api.onchange('degree')
    def _onchange_degree_delete_professional_license(self):
        if self.degree == 'high_school':
            self.professional_license = False

    @api.constrains('degree', 'professional_license')
    def _check_professional_license(self):
        for record in self:
            if record.degree in self.PROFESSIONAL_DEGREES and (not record.professional_license or not record.professional_license):
                raise ValidationError("The professional license is required for professional degrees")
            if (not record.degree) or (record.degree not in self.PROFESSIONAL_DEGREES):
                if record.professional_license:
                    raise ValidationError("The professional cannot be set unless degree is bachelor, master or doctorate")

    def toggle_activity(self):
        for record in self:
            record.activity = not record.activity

    def compute_age(self):
        today = date.today()
        for record in self:
            age = (today.year - record.birthdate.year)
            if (today.month, today.day) < (record.birthdate.month, record.birthdate.day):
                age-=1
                record.age = age
            else:
                record.age = age