# -*- coding: utf-8 -*-
{
   'name': "Mercado Libre conector",

   'summary': """Mercado Libre conector""",

   'description': """
        
    """,

   'author': "Wissen",

   'category': 'Uncategorized',
   'version': '14.0.1.0.4',

   'depends': ['base', 'mail', 'base_ml', 'stock', 'account', 'l10n_mx_edi', 'l10n_mx_edi_extended'],

   'data': [
       'data/data.xml',
       'security/ir.model.access.csv',
       'views/templates.xml',
       # 'views/sale_order_view.xml',
       'views/ml_notifications_view.xml',
       'views/ml_settings_view.xml',
       'wizard/ml_response_wizard_view.xml',
   ],
   'installable': True,
   'application': True,
    'license': 'LGPL-3',

}
