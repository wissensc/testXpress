# -*- coding: utf-8 -*-

from odoo import models, fields


class ResponseWizard(models.TransientModel):
    _name = 'ml.response.wizard'
    _description = 'MercadoLibre response wizard'

    response = fields.Text("Response", readonly=True)

