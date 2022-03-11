# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    id_buyer = fields.Char("Id Buyer", index=True, copy=False, readonly=True)

    _sql_constraints = [('id_buyer_unique', 'unique (id_buyer)', _('Buyer ID must be unique'))]