
from odoo.http import request
from odoo.http import Response
from odoo.http import content_disposition
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID, _, api, fields
from dateutil.parser import *
from datetime import timezone
from datetime import timedelta

import odoo.http as http
import hashlib
import re
import logging
import base64

_logger = logging.getLogger(__name__)


def ml_datetime(date_str):
    try:
        date_str = str(date_str)
        return parse(date_str).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    except:
        _logger.error(type(date_str))
        _logger.error(date_str)
        return None


class Main(http.Controller):

    @http.route('/ml_notifications', type='json', auth='public', methods=['POST'], cors='*', csrf=False)
    def ml_notifications(self):
        data_raw = request.jsonrequest
        # print(request.httprequest.environ['REMOTE_ADDR'])
        _logger.info(data_raw)
        ml_conf = request.env.ref('ml_connector.ml_settings_1').with_user(SUPERUSER_ID)

        if data_raw and ("error" in data_raw):
            return Response(data_raw['error'], content_type='text/html;charset=utf-8', status=data_raw['status'])
        else:
            if ml_conf.clientId == str(data_raw.get('application_id', '')) and ml_conf.userId == str(data_raw.get('user_id', '')):
                data = self.process_raw(data_raw)
                notification = request.env['ml.notifications'].with_user(SUPERUSER_ID)
                notification_id = notification.search([('resource', '=', data_raw['resource'])])

                if not notification_id:
                    notification_id = notification.create(data)
                    request.env.cr.commit()
                else:
                    notification_id.write(data)
                notification.process_topic(data, notification_id)
            else:
                return Response("<html><body><h5>Error</h5></body></html>", content_type='text/html;charset=utf-8', status=403)

        return None

    @http.route('/my_invoice/<int:invoice_id>', type='http', auth='public', website=True)
    def download(self, invoice_id, **kwargs):
        if kwargs.get('token', False) == self.mytoken(invoice_id, 'invoice'):
            url_pdf = '/my_invoice/%s/pdf?token=%s' % (invoice_id, kwargs.get('token', ''))
            url_xml = '/my_invoice/%s/xml?token=%s' % (invoice_id, kwargs.get('token', ''))
            return request.render('ml_connector.success', {'url_pdf': url_pdf, 'url_xml': url_xml, 'submitted': kwargs.get('submitted', False)})
        else:
            return request.render('http_routing.403')

    @http.route('/my_invoice/<int:invoice_id>/xml', type='http', auth='public', website=True)
    def download_xml(self, invoice_id, **kwargs):
        move = request.env['account.move'].with_user(SUPERUSER_ID).browse(invoice_id).exists()
        if kwargs.get('token', False) == self.mytoken(invoice_id, 'invoice'):
            return self._show_xml(move, download=True)
        else:
            return request.render('http_routing.403')

    @http.route('/my_invoice/<int:invoice_id>/pdf', type='http', auth='public', website=True)
    def download_pdf(self, invoice_id, **kwargs):
        move = request.env['account.move'].with_user(SUPERUSER_ID).browse(invoice_id).exists()
        if kwargs.get('token', False) == self.mytoken(invoice_id, 'invoice'):
            return self._show_report(model=move, report_type='pdf', report_ref='account.account_invoices',  download=True)
        else:
            return request.render('http_routing.403')

    @http.route('/my_sale/<int:sale_id>', type='http', auth="public", website=True)
    def invoice(self, sale_id, **kwargs):
        sale = request.env['sale.order'].with_user(SUPERUSER_ID).with_context().browse(sale_id).exists()

        if sale:
            id_buyer = sale.id_buyer
            kwargs['id_buyer'] = id_buyer or False
            buyer = request.env['res.partner'].with_user(SUPERUSER_ID).search([('id_buyer', '=', id_buyer)])
            token = self.mytoken(sale.id, 'sale')
            if kwargs.get('token') == token:
                if sale.invoice_ids and not kwargs.get('submitted'):
                    invoice = sale.invoice_ids[0]
                    return request.redirect('/my_invoice/{}?token={}'.format(invoice.id, self.mytoken(invoice.id, 'invoice')))
                if kwargs.get('buyer_name') and not kwargs.get('submitted'):
                    if self._expired(sale.date_order):
                        return request.render('ml_connector.expired', {})
                    buyer = request.env['res.partner'].with_user(SUPERUSER_ID).process_buyer(buyer, kwargs)
                    # the field returns False because it is disabled, the value of the disabled field is 31
                    invoice = sale._create_invoices_ws(partner=buyer, method_code='31', usage=kwargs.get('invoice_usage', ''))
                    invoice.action_post()
                    request.env.cr.commit()
                    invoice.action_process_edi_web_services()
                    request.env.cr.commit()

                    if invoice.edi_state == 'sent':
                        notification = request.env['ml.notifications'].with_user(SUPERUSER_ID).browse(sale.notification_id.id).exists()
                        note = notification.note
                        notification.state = 'success'
                        notification.note = _('%s, Invoice: %s', note, invoice.name)
                    else:
                        raise UserError(_("The invoice %s was not stamped", invoice.name))
                    return request.redirect('/my_invoice/{}?token={}&submitted=1'.format(invoice.id, self.mytoken(invoice.id, 'invoice')))
                if self._expired(sale.date_order):
                    return request.render('ml_connector.expired', {})
                return request.render('ml_connector.form_invoice',
                                      {'sale': sale, 'buyer': buyer,
                                       'usage': request.env['res.partner'].with_user(SUPERUSER_ID).catalog_usage(),
                                       'method': request.env['l10n_mx_edi.payment.method'].with_user(SUPERUSER_ID).search([])})
            else:
                return request.render('http_routing.403')
        else:
            return request.render('http_routing.404')

    def _show_xml(self, invoice, download=False):

        doc_edi = invoice.edi_document_ids
        format_edi = request.env.ref('l10n_mx_edi.edi_cfdi_3_3').with_user(SUPERUSER_ID)
        ir_attachment = doc_edi.filtered(lambda x: x.state == 'sent' and x.edi_format_id == format_edi).attachment_id

        if not ir_attachment:
            raise UserError(_("xml not found"))
        xml = ir_attachment.datas
        xml = base64.b64decode(xml)
        reporthttpheaders = [
            ('Content-Type', 'application/xml'),
            ('Content-Length', len(xml)),
        ]
        if download:
            filename = ir_attachment.name
            reporthttpheaders.append(('Content-Disposition', content_disposition(filename)))
        return request.make_response(xml, headers=reporthttpheaders)

    def _show_report(self, model, report_type, report_ref, download=False):
        if report_type not in ('html', 'pdf', 'text'):
            raise UserError(_("Invalid report type: %s", report_type))

        report_sudo = request.env.ref(report_ref).with_user(SUPERUSER_ID)

        if not isinstance(report_sudo, type(request.env['ir.actions.report'])):
            raise UserError(_("%s is not the reference of a report", report_ref))

        if hasattr(model, 'company_id'):
            report_sudo = report_sudo.with_company(model.company_id)

        method_name = '_render_qweb_%s' % (report_type)
        report = getattr(report_sudo, method_name)([model.id], data={'report_type': report_type})[0]
        reporthttpheaders = [
            ('Content-Type', 'application/pdf' if report_type == 'pdf' else 'text/html'),
            ('Content-Length', len(report)),
        ]
        if report_type == 'pdf' and download:
            filename = "%s.pdf" % (re.sub('\W+', '-', model._get_report_base_filename()))
            reporthttpheaders.append(('Content-Disposition', content_disposition(filename)))
        return request.make_response(report, headers=reporthttpheaders)

    def mytoken(self, model, tag):
        h = hashlib.sha224()
        string = "{}ws{}".format(model, tag)
        h.update(string.encode())
        return h.hexdigest()

    def _expired(self, datetime):
        current_date = fields.Datetime.context_timestamp(request, fields.Datetime.now() + timedelta(minutes=5))
        sale_date = fields.Datetime.context_timestamp(request, datetime)
        if current_date.year == sale_date.year and current_date.month == sale_date.month:
            return False
        return True

    @api.model
    def process_raw(self, data):
        vals = {
            "resource": data.get('resource', ''),
            "userId": data.get('user_id', ''),
            "topic": data.get('topic', ''),
            "applicationId": data.get('application_id', ''),
            "attempts": data.get('attempts', ''),
            "sent": ml_datetime(data.get('sent', '')),
            "received": ml_datetime(data.get('received', '')),
            "ml_notification": data,
        }
        return vals
