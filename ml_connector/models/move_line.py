# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.addons.ml_connector.mercadolibre import mercadolibre


class MoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model
    def create(self, vals):
        res = super(MoveLine, self).create(vals)
        if vals.get('product_id', False):
            product = self.env['product.product'].browse(vals.get('product_id'))
            product_id = product.product_tmpl_id
            if product_id.item_type:
                ml_conf = self.env.ref('ml_connector.ml_settings_1')
                ml = mercadolibre.ML(ml_conf.access_token)
                if product_id.item_type == '2':
                    ml.update_variation(product_id.id_item, product_id.id_variation, product_id.virtual_available)
                elif product_id.item_type == '1':
                    ml.update_stock(product_id.id_item, product_id.virtual_available)
        return res

    def write(self, vals):
        res = super(MoveLine, self).write(vals)
        if vals.get('product_id', False):
            product = self.env['product.product'].browse(vals.get('product_id'))
            product_id = product.product_tmpl_id
            if product_id.item_type:
                ml_conf = self.env.ref('ml_connector.ml_settings_1')
                ml = mercadolibre.ML(ml_conf.access_token)
                if product_id.item_type == '2':
                    ml.update_variation(product_id.id_item, product_id.id_variation, product_id.virtual_available)
                elif product_id.item_type == '1':
                    ml.update_stock(product_id.id_item, product_id.virtual_available)
        return res
