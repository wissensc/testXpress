# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    id_item = fields.Char('Id item', index=True, copy=False, compute='_compute_id_item', inverse='_set_id_item', store=True)
    id_variation = fields.Char('Id variation', index=True, copy=False, compute='_compute_id_variation', inverse='_set_id_variation', store=True)
    id_inventory = fields.Char('Id inventory', index=True, copy=False, compute='_compute_id_inventory', inverse='_set_id_inventory', store=True)

    item_type = fields.Selection([('1', 'Single'), ('2', 'With variants')],  string="Item type", copy=False, store=True,
                                 compute='_compute_item_type', inverse='_set_item_type', default=None)

    @api.depends('product_variant_ids', 'product_variant_ids.id_item')
    def _compute_id_item(self):
        self.id_item = False
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.id_item = template.product_variant_ids.id_item

    def _set_id_item(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.id_item = self.id_item

    @api.depends('product_variant_ids', 'product_variant_ids.id_variation')
    def _compute_id_variation(self):
        self.id_variation = False
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.id_variation = template.product_variant_ids.id_variation

    def _set_id_variation(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.id_variation = self.id_variation


    @api.depends('product_variant_ids', 'product_variant_ids.id_inventory')
    def _compute_id_inventory(self):
        self.id_inventory = False
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.id_inventory = template.product_variant_ids.id_inventory

    def _set_id_inventory(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.id_inventory = self.id_inventory

    @api.depends('product_variant_ids', 'product_variant_ids.item_type')
    def _compute_item_type(self):
        self.item_type = False
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.item_type = template.product_variant_ids.item_type

    def _set_item_type(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.item_type = self.item_type

    @api.model_create_multi
    def create(self, vals_list):
        templates = super(ProductTemplate, self).create(vals_list)
        if "create_product_product" not in self._context:
            templates._create_variant_ids()

        # This is needed to set given values to first variant after creation
        for template, vals in zip(templates, vals_list):
            related_vals = {}
            if vals.get('id_item'):
                related_vals['id_item'] = vals['id_item']
            if vals.get('id_variation'):
                related_vals['id_variation'] = vals['id_variation']
            if vals.get('id_inventory'):
                related_vals['id_inventory'] = vals['id_inventory']
            if vals.get('item_type'):
                related_vals['item_type'] = vals['item_type']
            if related_vals:
                template.write(related_vals)

        return templates