# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.ml_connector.mercadolibre import mercadolibre

import requests
import logging

_logger = logging.getLogger(__name__)


class MlSettings(models.Model):
    _name = 'ml.settings'
    _description = 'Settings Mercadolibre'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    clientId = fields.Char('Client id')
    client_secret = fields.Char('Client secret')

    name = fields.Char('Code')
    redirect_uri = fields.Char('Redirect uri')

    access_token = fields.Char('Access token')
    refresh_token = fields.Char('Refresh token')

    userId = fields.Char('User id', readonly='True')
    state = fields.Selection([('disconnected', 'Disconnected'), ('connected', 'Connected')],
                             default='disconnected', string="State", tracking="1")
    ml_response = fields.Text("Mercado Libre response", readonly=True)
    update_datetime = fields.Datetime("date for last request", readonly=True)

    nickname = fields.Char("Nickname", readonly=True)
    username = fields.Char("Username", readonly=True)

    product_id = fields.Many2one('product.product', string="Product shipping")
    location_id = fields.Many2one('stock.location', string="Location")
    route_id = fields.Many2one('stock.location.route', string="Route")

    def name_get(self):
        result = []
        for record in self:
            rec_name = _("Settings")
            result.append((record.id, rec_name))
        return result

    def get_token(self):
        ml = mercadolibre.ML(self.clientId, self.client_secret, self.name, self.redirect_uri)
        access_data = ml.get_access_token()
        info = access_data["response"]
        _logger.info(info)
        self.ml_response = info
        self.update_datetime = fields.datetime.now()

        if access_data["status"] == requests.codes.ok:
            self.state = 'connected'
            self.access_token = info['access_token']
            self.refresh_token = info['refresh_token']
            self.userId = info['user_id']
            ml2 = mercadolibre.ML(info['access_token'])
            info_user = ml2.get_user(self.userId)
            self.nickname = info_user['response']['nickname']
            self.username = "{} {}".format(info_user['response']['first_name'], info_user['response']['last_name']).strip()
        else:
            self.state = 'disconnected'
            return {
                'name': _('Failed connection'),
                'type': 'ir.actions.act_window',
                'res_model': 'ml.response.wizard',
                'view_mode': 'form',
                'context': {
                    'default_response': self.ml_response,
                    },
                'target': 'new'
            }

    def get_refresh_token(self):
        ml = mercadolibre.ML(self.clientId, self.client_secret, self.refresh_token)
        access_data = ml.get_refresh_token()
        info = access_data["response"]
        _logger.info(info)
        self.update_datetime = fields.datetime.now()
        self.ml_response = info

        if access_data["status"] == requests.codes.ok:
            self.state = 'connected'
            self.access_token = info['access_token']
            self.refresh_token = info['refresh_token']
            self.userId = info['user_id']
            ml2 = mercadolibre.ML(info['access_token'])
            info_user = ml2.get_user(self.userId)
            self.nickname = info_user['response']['nickname']
            self.username = "{} {}".format(info_user['response']['first_name'],
                                           info_user['response']['last_name']).strip()
        else:
            self.state = 'disconnected'
            return {
                'name': _('Failed connection'),
                'type': 'ir.actions.act_window',
                'res_model': 'ml.response.wizard',
                'view_mode': 'form',
                'context': {
                    'default_response': self.ml_response,
                    },
                'target': 'new'
            }

    def get_new_code(self):
        state_url = fields.datetime.now().strftime('ws%y%m%d-%H%M%S')
        url = 'https://auth.mercadolibre.com.mx/authorization?response_type=code&client_id={}&state={}&redirect_uri={}'.format(self.clientId, state_url, self.redirect_uri)
        _logger.info(url)
        self.state = 'disconnected'
        self.access_token = None
        self.refresh_token = None
        self.userId = None
        self.ml_response = None
        self.nickname = None
        self.username = None
        self.update_datetime = fields.datetime.now()
        return {
         'type': 'ir.actions.act_url',
         'target': 'new',
         'url': url
        }

