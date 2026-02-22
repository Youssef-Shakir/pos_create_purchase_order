# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import base64


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    pos_origin = fields.Boolean(string='From POS', default=False)
    pos_config_id = fields.Many2one('pos.config', string='POS Config')
    pos_bill_reference = fields.Char(string='Vendor Bill Reference')
    pos_receipt_image = fields.Binary(string='Receipt Image', attachment=True)
    pos_paid_with_cash = fields.Boolean(string='Paid with POS Cash', default=False)

    def action_view_receipt_image(self):
        """Open receipt image in a popup"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt Image'),
            'res_model': 'purchase.order',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('pos_create_purchase_order.purchase_order_receipt_image_form').id,
            'target': 'new',
        }

    @api.model
    def create_purchase_order_from_pos(self, partner_id, orderlines, cashier_id, po_state, session_id,
                                        pay_with_cash=False, bill_reference=False, receipt_image=False):
        """Create purchase order from POS with optional payment"""
        pos_session = self.env['pos.session'].browse(session_id)
        if not pos_session:
            return False

        order_vals = {
            'partner_id': partner_id,
            'user_id': cashier_id,
            'origin': pos_session.name,
            'pos_origin': True,
            'pos_config_id': pos_session.config_id.id,
            'pos_bill_reference': bill_reference or False,
            'pos_paid_with_cash': pay_with_cash,
        }

        # Handle receipt image
        if receipt_image:
            # Remove data URL prefix if present
            if ',' in receipt_image:
                receipt_image = receipt_image.split(',')[1]
            order_vals['pos_receipt_image'] = receipt_image

        order = self.create(order_vals)

        total_amount = 0
        for line_data in orderlines:
            product_data = line_data.get('product', {})
            product_id = product_data.get('id')

            if not product_id:
                continue

            product = self.env['product.product'].browse(product_id)
            quantity = product_data.get('quantity', 1)
            price = product_data.get('price', 0)
            total_amount += quantity * price

            tax_ids = product.supplier_taxes_id.ids or []

            line_vals = {
                'order_id': order.id,
                'product_id': product_id,
                'name': product.display_name,
                'product_qty': quantity,
                'price_unit': price,
                'product_uom': product_data.get('uom_id') or product.uom_po_id.id or product.uom_id.id,
                'taxes_id': [(6, 0, tax_ids)],
                'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            }
            self.env['purchase.order.line'].create(line_vals)

        # Handle PO state transitions
        if po_state == 'sent':
            order.action_rfq_send()
            order.write({'state': 'sent'})

        elif po_state == 'purchase':
            order.button_confirm()

        elif po_state == 'to approve':
            order.write({'state': 'to approve'})

        elif po_state == 'done':
            order.button_confirm()
            order.button_done()

        import logging
        _logger = logging.getLogger(__name__)

        result = {
            'po_name': order.name,
            'po_id': order.id,
            'payment_created': False,
            'payment_error': False,
        }

        # Create payment and cash out if paying with POS cash
        if pay_with_cash and total_amount > 0:
            _logger.info("Creating payment for PO %s, amount: %s, pay_with_cash: %s",
                        order.name, total_amount, pay_with_cash)
            payment_result = self._create_pos_cash_payment(
                order, pos_session, partner_id, total_amount, bill_reference
            )
            result['payment_created'] = payment_result
            if not payment_result:
                result['payment_error'] = True
                _logger.warning("Payment creation failed for PO %s", order.name)
        else:
            _logger.info("Skipping payment: pay_with_cash=%s, total_amount=%s",
                        pay_with_cash, total_amount)

        return result

    def _create_pos_cash_payment(self, order, pos_session, partner_id, amount, bill_reference):
        """Create cash out in POS session with partner for reconciliation"""
        import logging
        _logger = logging.getLogger(__name__)

        partner = self.env['res.partner'].browse(partner_id)
        _logger.info("Creating POS cash out: partner=%s, amount=%s", partner.name, amount)

        return self._create_pos_cash_out(pos_session, amount, order.name, bill_reference, partner)

    def _create_pos_cash_out(self, pos_session, amount, po_name, bill_reference, partner=None):
        """Record cash out in POS session as a bank statement line with partner"""
        import logging
        _logger = logging.getLogger(__name__)

        try:
            # Build payment reference
            payment_ref = _('%s - Cash Out - Purchase Order: %s') % (pos_session.name, po_name)
            if bill_reference:
                payment_ref += ' (' + bill_reference + ')'

            # Get the cash journal
            cash_journal = None

            if hasattr(pos_session, 'cash_journal_id') and pos_session.cash_journal_id:
                cash_journal = pos_session.cash_journal_id

            if not cash_journal:
                cash_payment_method = pos_session.config_id.payment_method_ids.filtered(
                    lambda pm: pm.is_cash_count
                )[:1]
                if cash_payment_method:
                    cash_journal = cash_payment_method.journal_id

            if not cash_journal:
                _logger.warning("No cash journal found for cash out on session %s", pos_session.name)
                return False

            # Get the counterpart account - use partner's payable account
            counterpart_account = None
            if partner and partner.property_account_payable_id:
                counterpart_account = partner.property_account_payable_id
            else:
                counterpart_account = self.env['account.account'].search([
                    ('company_id', '=', pos_session.company_id.id),
                    ('account_type', '=', 'liability_payable'),
                ], limit=1)

            # Create bank statement line for cash out with partner
            statement_line_vals = {
                'pos_session_id': pos_session.id,
                'journal_id': cash_journal.id,
                'amount': -amount,  # Negative for cash out
                'date': fields.Date.context_today(self),
                'payment_ref': payment_ref,
                'partner_id': partner.id if partner else False,  # Assign partner for reconciliation
            }

            if counterpart_account:
                statement_line_vals['counterpart_account_id'] = counterpart_account.id

            statement_line = self.env['account.bank.statement.line'].create(statement_line_vals)
            _logger.info("Created cash out statement line %s for %s with partner %s",
                        statement_line.id, po_name, partner.name if partner else 'None')
            return True

        except Exception as e:
            _logger.error("Failed to create POS cash out: %s", str(e), exc_info=True)
            return False
