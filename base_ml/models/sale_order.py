# -*- coding: utf-8 -*-

from odoo import fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    id_order = fields.Char("Id Order", index=True, readonly=True, copy=False)
    id_buyer = fields.Char("Id Buyer", index=True, readonly=True, copy=False)
    state_order = fields.Char("Status order", index=True, readonly=True, copy=False)

    _sql_constraints = [('id_order_unique', 'unique (id_order)', _('Order ID must be unique'))]
