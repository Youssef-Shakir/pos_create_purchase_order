# -*- coding: utf-8 -*-
{
    'name': 'POS Create Purchase Order',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Create Purchase Orders directly from POS screen',
    'description': """
POS Create Purchase Order
=========================
This module allows users to create purchase orders directly from the Point of Sale screen.

Features:
- Create purchase order from POS with one click
- Configure PO state (Draft, RFQ Sent, To Approve, Purchase Order, Locked)
- View purchase orders created from each POS config
- Filter and group purchase orders by POS origin
    """,
    'author': 'Donialink, Yousif Shakir',
    'website': 'https://www.donialink.com',
    'depends': ['point_of_sale', 'purchase', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_create_purchase_order/static/src/js/purchase_order_popup.js',
            'pos_create_purchase_order/static/src/js/create_purchase_button.js',
            'pos_create_purchase_order/static/src/xml/purchase_order_popup.xml',
            'pos_create_purchase_order/static/src/xml/create_purchase_button.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
