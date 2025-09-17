from odoo import models, fields, api
from datetime import date
import random

class Student(models.Model):
    _name = 'school.student'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    credential_number = fields.Char(
        string='Credential number'
    )
    name = fields.Char(
        string = 'Name'
    )
    birthdate = fields.Date(
        string = 'Birthdate'
    )
    age = fields.Integer(
        string = "Age",
        compute = "compute_age"
    )
    cellphone = fields.Char(
        string='Cellphone number'
    )
    email = fields.Char(
        string='Email',
        default='',
        compute = '_compute_email',
    )
    grade_level = fields.Selection(
        [
            ('elementary_school', 'Elementary school'),
            ('junior_highschool', 'Junior high'),
            ('highschool', 'High school'),
        ],
        string='Grade level',
        required=True
    )
    group = fields.Char(
        string='Group',
        required=True
    )
    active = fields.Boolean(
        string='Enrolled',
        default=True
    )
    emergency_contact_ids = fields.One2many(
        comodel_name='emergency.contact',
        inverse_name='student_id',
        string='Emergency contact name'
    )

    def compute_age(self):
        today = date.today()
        for record in self:
            if not record.birthdate:
                age = 0
                continue
            age = (today.year - record.birthdate.year)
            if (today.month, today.day) < (record.birthdate.month, record.birthdate.day):
                age -= 1
                record.age = age
            else:
                record.age = age

    @api.depends('credential_number')
    def _compute_email(self):
        for record in self:
            record.email = f"{record.credential_number}@estudiantes.uv.mx"

    def compute_dni(self):
        num_unavailable = []
        for record in self:
            num = random.randint(10, 99)
            if num in num_unavailable:
                num = random.randint(10, 99)
            else:
                num_unavailable.append(num)
                record.credential_number = f"S220170{num}"


