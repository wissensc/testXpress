# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    id_item = fields.Char('Id item', index=True, copy=False)
    id_variation = fields.Char('Id variation', index=True, copy=False)
    id_inventory = fields.Char('Id inventory', index=True, copy=False)

    item_type = fields.Selection([('1', 'Single'), ('2', 'With variants')],  string="Item type", copy=False, default=None)

