# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import AccessError
from odoo.addons.ml_connector.mercadolibre import mercadolibre

import hashlib
import logging
import requests

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    notification_id = fields.Many2one('ml.notifications', string="Notification", copy=False, readonly=True, index=True, ondelete='restrict')

    _sql_constraints = [('notification_id_unique', 'unique (notification_id)', _('Notification ID must be unique'))]

    def invoice_link(self, pack_id):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = base_url + '/my_sale/{}?token={}'.format(self.id, self.mytoken(self.id, 'sale'))
        _logger.info(url)
        ml_conf = self.env.ref('ml_connector.ml_settings_1')
        ml = mercadolibre.ML(ml_conf.access_token)
        text = _("Si deseas facturar, entra en el siguiente <a href='%s'>enlace</a> para registrar tus datos", url)
        data = ml.send_message(text, pack_id, self.notification_id.userId, self.id_buyer)
        _logger.info(data)
        note = self.notification_id.note
        if data['status'] == requests.codes.ok or data['status'] == 201:
            self.notification_id.note = "{} {}".format(note, _("link sent"))
        else:
            self.notification_id.state = 'failed'
            self.notification_id.note = "{} {}".format(note, data['response'].get('error', ''))
        return url


    def _prepare_invoice_line_ws(self, order_line):
        return {
            'product_id': order_line.product_id.id,
            'quantity': order_line.qty if self.amount_total >= 0 else -order_line.qty,
            'discount': order_line.discount,
            'price_unit': order_line.price_unit,
            'name': order_line.product_id.display_name,
            'tax_ids': [(6, 0, order_line.tax_ids_after_fiscal_position.ids)],
            'product_uom_id': order_line.product_uom_id.id,
        }

    def _prepare_invoice_ws(self, partner):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

        invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': partner.id,
            # 'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_payment_term_id': self.payment_term_id.id,
            # 'payment_reference': self.reference,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'l10n_mx_edi_payment_method_id':  1,
            'l10n_mx_edi_usage': 'G01'
        }
        return invoice_vals


    def _create_invoices_ws(self, partner, method_code, usage):
        """
         Create the invoice associated to the SO.
         :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                         (partner_invoice_id, currency)
         :param final: if True, refunds will be generated if necessary
         :returns: list of created invoices
         """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0  # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            current_section_vals = None
            down_payments = order.env['sale.order.line']

            invoice_vals = order._prepare_invoice_ws(partner)

            method = self.env['l10n_mx_edi.payment.method'].search([('code', '=', method_code)])
            invoice_vals.update(l10n_mx_edi_payment_method_id=method.id, l10n_mx_edi_usage=usage)
            invoiceable_lines = order._get_invoiceable_lines(True)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    invoice_line_vals.append(
                        (0, 0, order._prepare_down_payment_section_line(sequence=invoice_item_sequence, )), )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                invoice_line_vals.append((0, 0, line._prepare_invoice_line(sequence=invoice_item_sequence, )), )
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise self._nothing_to_invoice_error()


        # 3) Create invoices.
        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].with_context(default_move_type='out_invoice').create(invoice_vals_list)
        # self.env.cr.commit()

        for move in moves:
            move.message_post_with_view('mail.message_origin_link',
                                        values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
                                        subtype_id=self.env.ref('mail.mt_note').id)
        moves.action_post()
        moves.action_process_edi_web_services()
        return moves

    def _items(self, raw_data):
        lines = []
        line = {}
        for item in raw_data['order_items']:
            item_id = item['item']['id']
            variation_id = item['item'].get('variation_id')
            if variation_id:
                tmpl = self.env['product.template'].search([('item_type', '=', '2'), ('id_item', '=', item_id), ('id_variation', '=', variation_id)])
            else:
                tmpl = self.env['product.template'].search([('item_type', '=', '1'), ('id_item', '=', item_id)])
            if tmpl:
                product = self.env['product.product'].search([('product_tmpl_id', '=', tmpl.id)])
                line['product_id'] = product.id
                line['name'] = product.name
                line['product_uom_qty'] = item['quantity']
                price_untax = float(item['unit_price']) / 1.16
                line['price_unit'] = price_untax
                # 'qty_delivered': 1,
                # 'product_uom': self.company_data['product_order_cost'].uom_id.id,
                # 'discount': 2.00,
                line['tax_id'] = [(4, self.env.ref('l10n_mx.1_tax12').id)]
                lines.append(line)
            else:
                return []
        return lines

    @api.model
    def process_raw(self, data):
        sales_generic = self.env.ref('base_ml.sales_generic')
        order_lines = self._items(data)
        if not data.get('buyer')['id']:
            return {'error': _('No buyer found')}
        if not order_lines:
            return {'error': _('No product found')}

        return {
                'id_order': data['id'],
                'id_buyer': data['buyer']['id'],
                'partner_id': sales_generic.id,
                # 'partner_invoice_id': ml_buyer.id,
                # 'partner_shipping_id': ml_buyer.id,
                # 'analytic_account_id': self.analytic_account.id,
                # 'pricelist_id': self.pricelist.id,
                'order_line': [(0, 0, item) for item in order_lines],
                # 'picking_policy': 'direct',
                'team_id': self.env.ref('base_ml.team_meli').id,
                'tag_ids': [(4, self.env.ref('base_ml.tag_meli').id)],
                # 'warehouse_id':
                # 'company_id':
                'payment_term_id': self.env.ref('account.account_payment_term_immediate').id
            }

    def mytoken(self, model, tag):
        h = hashlib.sha224()
        string = "{}ws{}".format(model, tag)
        h.update(string.encode())
        return h.hexdigest()
