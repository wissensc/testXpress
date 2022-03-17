# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.addons.ml_connector.mercadolibre import mercadolibre


class MoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _update_stock_ml(self, product_id):
        if product_id.item_type:
            ml_conf = self.env.ref('ml_connector.ml_settings_1')
            location_id = ml_conf.location_id
            availability = self.env['stock.quant']._get_available_quantity(product_id, location_id)
            ml = mercadolibre.ML(ml_conf.access_token)
            if product_id.item_type == '2':
                ml.update_variation(product_id.id_item, product_id.id_variation, availability)
            elif product_id.item_type == '1':
                ml.update_stock(product_id.id_item, availability)

    @api.model
    def create(self, vals):
        res = super(MoveLine, self).create(vals)
        product_id = vals.get('product_id')
        if product_id:
            product = self.env['product.product'].browse(product_id)
            self._update_stock_ml(product)
        return res

    def write(self, vals):
        res = super(MoveLine, self).write(vals)
        product_id = vals.get('product_id') or self.product_id.id
        if product_id:
            product = self.env['product.product'].browse(product_id)
            self._update_stock_ml(product)
        return res
