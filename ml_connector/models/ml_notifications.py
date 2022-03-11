# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.addons.ml_connector.mercadolibre import mercadolibre

import requests
import logging

_logger = logging.getLogger(__name__)


class MlNotifications(models.Model):
    _name = 'ml.notifications'
    _description = 'Notification MercadoLibre'
    _order = 'write_date desc'

    resource = fields.Char('Resource', index=True)
    topic = fields.Char('Topic')
    attempts = fields.Char('Attempts')
    sent = fields.Datetime('Sent')
    received = fields.Datetime('Received')
    userId = fields.Char('User id')
    applicationId = fields.Char('Application id')
    ml_notification = fields.Text("Mercado Libre notification")
    state = fields.Selection([("received", "Received"),
                              ("processing", "Processing"),
                              ("failed", "Process with errors"),
                              ("success", "Processed")],
                             string='State', index=True, default="received")
    note = fields.Char()

    @api.model
    def process_topic(self, vals, notification):
        if vals['topic'] == "orders_v2":
            resource = vals['resource']
            order_id = resource.split('/')[2]
            sale = self.env['sale.order'].search([('id_order', '=', order_id)])
            if sale:
                return None
            data_raw = notification.function_notification_details(vals['resource'], vals['topic'])
            if data_raw:
                data = self.env['sale.order'].process_raw(data_raw['response'])
                if data_raw['response']['status'] == 'paid' and not data.get('error', False):
                    data['notification_id'] = notification.id
                    sale = self.env['sale.order'].create(data)
                    # self.env.cr.commit()
                    sale.action_confirm()
                    notification.write({'state': 'processing', 'note': _('Order: %s', sale.name)})
                    if data_raw['response'].get('pack_id'):
                        sale.invoice_link(data_raw['response']['pack_id'])
                    else:
                        sale.invoice_link(data_raw['response']['id'])
                else:
                    notification.write({'state': 'failed', 'note': data['error']})

    def function_notification_details(self, resource, topic):
        ml_conf = self.env.ref('ml_connector.ml_settings_1')
        ml = mercadolibre.ML(ml_conf.access_token)
        access_data = ml.get_notification_details(resource, topic)
        _logger.info(access_data['response'])
        if access_data['status'] == requests.codes.ok:
            self.state = 'processing'
        else:
            self.state = "failed"
            self.note = access_data['response'].get('error', '')
            if access_data['response']['message'] == 'Invalid token':
                ml_conf.state = 'disconnected'
                ml_conf.update_datetime = fields.datetime.now()
            return None
        return access_data

    def action_notification_details(self):
        ml_conf = self.env.ref('ml_connector.ml_settings_1')
        ml = mercadolibre.ML(ml_conf.access_token)

        data = ml.get_notification_details(self.resource, self.topic)
        return {
                'name': _('Details'),
                'type': 'ir.actions.act_window',
                'res_model': 'ml.response.wizard',
                'view_mode': 'form',
                'context': {
                    'default_response': data['response'],
                },
                'target': 'new'
            }

    def action_notification(self):
        return {
                'name': _('Notification'),
                'type': 'ir.actions.act_window',
                'res_model': 'ml.response.wizard',
                'view_mode': 'form',
                'context': {
                    'default_response': self.ml_notification,
                },
                'target': 'new'
            }
