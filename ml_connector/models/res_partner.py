# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def catalog_usage(self):
        return [('G01', 'Adquisición de mercancías'), ('G02', 'Devoluciones, descuentos o bonificaciones'),
                   ('G03', 'Gastos en general'), ('I01', 'Construcciones'),
                   ('I02', 'Mobilario y equipo de oficina por inversiones'), ('I03', 'Equipo de transporte'),
                   ('I04', 'Equipo de cómputo y accesorios'), ('I05', 'Dados, troqueles, moldes, matrices y herramental'),
                   ('I06', 'Comunicaciones telefónicas'), ('I07', 'Comunicaciones satelitales'),
                   ('I08', 'Otra maquinaria y equipo'), ('D01', 'Honorarios médicos, dentales y gastos hospitalarios'),
                   ('D02', 'Gastos médicos por incapacidad o discapacidad'), ('D03', 'Gastos funerales'),
                   ('D04', 'Donativos'),
                   ('D05', 'Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)'),
                   ('D06', 'Aportaciones voluntarias al SAR'), ('D07', 'Primas por seguros de gastos médicos'),
                   ('D08', 'Gastos de transportación escolar obligatoria.'),
                   ('D09', 'Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones.'),
                   ('D10', 'Pagos por servicios educativos (colegiaturas)'), ('P01', 'Por definir')]

    def process_buyer(self, buyer, kwargs):
        data = {
            'name': kwargs.get('buyer_name', ''),
            'street_name': kwargs.get('buyer_address', ''),
            'vat': kwargs.get('buyer_rfc', ''),
            'zip': kwargs.get('buyer_zip', ''),
            'email': kwargs.get('buyer_email', ''),
            'phone': kwargs.get('buyer_phone', ''),
            'id_buyer': kwargs.get('id_buyer', '')
        }
        if buyer:
            data.pop('id_buyer')
            buyer.write(data)
        else:
            buyer = self.env['res.partner'].create(data)
        return buyer
