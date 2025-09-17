from odoo import fields, models,api
from datetime import date

class EmergencyContact(models.Model):
    _name = 'emergency.contact'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string = 'Name',
        required=True,
    )
    birthdate = fields.Date(
        string = 'Birthdate',
        required=True,
    )
    age = fields.Integer(
        string = 'Age',
        compute='_compute_age',
    )
    cellphone = fields.Char(
        string = 'Cellphone number',
        required=True
    )
    home_number = fields.Char(
        string = 'Home number',
        required=True
    )
    street = fields.Char(
        string = 'Street',
        required=True
    )
    street2 = fields.Char(
        string = 'Street 2',
        required=False
    )
    city = fields.Char(
        string = 'City',
        required=True
    )
    state = fields.Char(
        string = 'State',
        required=True
    )
    zip = fields.Char(
        string='Zip scode',
        required=True
    )

    relationship = fields.Selection(
        [
            ('mother', 'Mother'),
            ('father', 'Father'),
            ('sister', 'Sister'),
            ('brother', 'Brother'),
            ('grandparent', 'Grandparent'),
        ]
    )
    student_id = fields.Many2one(
        comodel_name = 'school.student',
        string = 'Student name',
        required=True,
    )

    @api.depends('birthdate')
    def _compute_age(self):
        for rec in self:
            today = date.today()
            age = today.year - rec.birthdate.year
            if (today.month, today.day) < (rec.birthdate.month, rec.birthdate.day):
                age -= 1
            else:
                rec.age = age