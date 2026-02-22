# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def action_reconcile_with_po_bill(self):
        """Reconcile this payment line with the PO bill from the wizard context"""
        self.ensure_one()

        # Try to get wizard from context first
        wizard_id = self.env.context.get('wizard_id')
        if wizard_id:
            wizard = self.env['po.quick.process'].browse(wizard_id)
            if wizard.exists():
                return wizard.action_reconcile_single_line(self.id)

        # Fallback: Find the most recent wizard for this partner's PO
        wizard = self.env['po.quick.process'].search([
            ('partner_id', '=', self.partner_id.id)
        ], order='id desc', limit=1)

        if not wizard:
            raise UserError(_('No active Quick Process wizard found.'))

        return wizard.action_reconcile_single_line(self.id)
