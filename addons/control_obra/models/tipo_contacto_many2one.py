from odoo import fields, models, api


class TipoContacto(models.Model):
    _name = 'tipo.contacto'
    _description = 'Tipo de Contacto'

    name = fields.Char(
        string='Tipo de Contacto',
        required=True)


    res_partner = fields.One2many(
        'res.partner',
        'tipo_contacto',
        string='Contactos Relacionados',
    )
