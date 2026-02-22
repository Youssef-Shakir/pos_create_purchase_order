# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    create_po = fields.Boolean(string='Create Purchase Order',
                               help='Enable creating purchase orders from POS')
    po_state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked')
    ], string='PO State', default='draft',
       help='State of the purchase order when created from POS')
    po_vendor_id = fields.Many2one('res.partner', string='Default Vendor',
                                   domain="[('is_company', '=', True)]",
                                   help='Default vendor for purchase orders created from POS')


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        result['search_params']['fields'].extend(['create_po', 'po_state', 'po_vendor_id'])
        return result


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    create_po = fields.Boolean(related='pos_config_id.create_po', readonly=False)
    po_state = fields.Selection(related='pos_config_id.po_state', readonly=False)
    po_vendor_id = fields.Many2one(related='pos_config_id.po_vendor_id', readonly=False)
