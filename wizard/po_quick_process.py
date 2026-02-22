# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class POQuickProcess(models.TransientModel):
    _name = 'po.quick.process'
    _description = 'Quick Process Purchase Order'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', required=True)

    # Related fields
    partner_id = fields.Many2one(related='purchase_order_id.partner_id', string='Vendor')
    currency_id = fields.Many2one(related='purchase_order_id.currency_id')
    amount_total = fields.Monetary(related='purchase_order_id.amount_total', string='Total')
    po_state = fields.Selection(related='purchase_order_id.state', string='PO Status')
    date_order = fields.Datetime(related='purchase_order_id.date_order', string='Order Date')
    order_line_ids = fields.One2many(related='purchase_order_id.order_line', string='Order Lines')
    picking_ids = fields.Many2many(related='purchase_order_id.picking_ids', string='Receipts')
    invoice_ids = fields.Many2many(related='purchase_order_id.invoice_ids', string='Bills')
    pos_origin = fields.Boolean(related='purchase_order_id.pos_origin')
    pos_paid_with_cash = fields.Boolean(related='purchase_order_id.pos_paid_with_cash')
    pos_bill_reference = fields.Char(related='purchase_order_id.pos_bill_reference')

    # Computed status
    is_confirmed = fields.Boolean(compute='_compute_status', string='Confirmed')
    all_received = fields.Boolean(compute='_compute_status', string='All Received')
    bill_created = fields.Boolean(compute='_compute_status', string='Bill Created')
    bill_posted = fields.Boolean(compute='_compute_status', string='Bill Posted')
    fully_paid = fields.Boolean(compute='_compute_status', string='Fully Paid')
    amount_due = fields.Monetary(compute='_compute_status', string='Amount Due')

    # Payment fields
    payment_journal_id = fields.Many2one('account.journal', string='Payment Journal',
                                          domain="[('type', 'in', ['bank', 'cash'])]")
    payment_amount = fields.Monetary(string='Payment Amount', currency_field='currency_id')
    payment_date = fields.Date(string='Payment Date', default=fields.Date.today)
    payment_memo = fields.Char(string='Memo')

    # Outstanding debits (unreconciled payments) for this vendor
    outstanding_debit_ids = fields.Many2many(
        'account.move.line', compute='_compute_outstanding_debits',
        string='Outstanding Payments'
    )
    outstanding_debit_count = fields.Integer(compute='_compute_outstanding_debits')

    @api.depends('purchase_order_id', 'purchase_order_id.state', 'purchase_order_id.picking_ids',
                 'purchase_order_id.invoice_ids')
    def _compute_status(self):
        for wizard in self:
            po = wizard.purchase_order_id
            if po:
                wizard.is_confirmed = po.state in ('purchase', 'done')

                # Check if all pickings are done
                pickings = po.picking_ids.filtered(lambda p: p.state != 'cancel')
                wizard.all_received = all(p.state == 'done' for p in pickings) if pickings else False

                # Check bills
                invoices = po.invoice_ids.filtered(lambda m: m.move_type == 'in_invoice')
                wizard.bill_created = bool(invoices)

                posted_invoices = invoices.filtered(lambda m: m.state == 'posted')
                wizard.bill_posted = bool(posted_invoices)

                amount_due = sum(inv.amount_residual for inv in posted_invoices)
                wizard.amount_due = amount_due
                wizard.fully_paid = amount_due <= 0 and wizard.bill_posted
            else:
                wizard.is_confirmed = False
                wizard.all_received = False
                wizard.bill_created = False
                wizard.bill_posted = False
                wizard.fully_paid = False
                wizard.amount_due = 0

    @api.depends('purchase_order_id', 'partner_id')
    def _compute_outstanding_debits(self):
        """Find unreconciled payments (debits on payable) for this vendor"""
        for wizard in self:
            if wizard.purchase_order_id and wizard.partner_id:
                # Vendor payments create DEBIT entries on payable accounts
                # These have positive amount_residual (money we've paid but not matched to bills)
                lines = self.env['account.move.line'].search([
                    ('partner_id', '=', wizard.partner_id.id),
                    ('account_id.account_type', '=', 'liability_payable'),
                    ('reconciled', '=', False),
                    ('amount_residual', '>', 0),  # Debits have positive residual
                    ('parent_state', '=', 'posted'),
                ], limit=20)
                wizard.outstanding_debit_ids = lines
                wizard.outstanding_debit_count = len(lines)
            else:
                wizard.outstanding_debit_ids = False
                wizard.outstanding_debit_count = 0

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            po = self.env['purchase.order'].browse(active_id)
            res['purchase_order_id'] = po.id
            # Default cash journal
            cash_journal = self.env['account.journal'].search([
                ('type', '=', 'cash'),
                ('company_id', '=', po.company_id.id)
            ], limit=1)
            if cash_journal:
                res['payment_journal_id'] = cash_journal.id
        return res

    @api.onchange('amount_due')
    def _onchange_amount_due(self):
        """Set default payment amount to amount due"""
        if self.amount_due > 0:
            self.payment_amount = self.amount_due

    def action_confirm_po(self):
        """Confirm the Purchase Order"""
        self.ensure_one()
        if self.purchase_order_id.state in ('draft', 'sent', 'to approve'):
            self.purchase_order_id.button_confirm()
        return self._refresh()

    def action_receive_all(self):
        """Receive all pending items"""
        self.ensure_one()
        for picking in self.purchase_order_id.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
            picking.button_validate()
        return self._refresh()

    def action_view_picking(self):
        """Open picking list"""
        self.ensure_one()
        pickings = self.purchase_order_id.picking_ids
        if len(pickings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': pickings.id,
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', pickings.ids)],
        }

    def action_create_bill(self):
        """Create vendor bill"""
        self.ensure_one()
        if not self.bill_created:
            self.purchase_order_id.action_create_invoice()
        return self._refresh()

    def action_post_bill(self):
        """Post the vendor bill"""
        self.ensure_one()
        for invoice in self.purchase_order_id.invoice_ids.filtered(lambda m: m.state == 'draft'):
            if not invoice.invoice_date:
                invoice.invoice_date = fields.Date.today()
            # Set bill reference from POS if available
            if self.pos_bill_reference and not invoice.ref:
                invoice.ref = self.pos_bill_reference
            invoice.action_post()
        return self._refresh()

    def action_view_bill(self):
        """Open bill"""
        self.ensure_one()
        invoices = self.purchase_order_id.invoice_ids.filtered(lambda m: m.move_type == 'in_invoice')
        if len(invoices) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoices.id,
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
        }

    def action_register_payment(self):
        """Create and post payment, then reconcile"""
        self.ensure_one()

        if not self.payment_journal_id:
            raise UserError(_('Please select a payment journal.'))

        if not self.payment_amount or self.payment_amount <= 0:
            raise UserError(_('Payment amount must be greater than zero.'))

        # Get unpaid bills
        invoices = self.purchase_order_id.invoice_ids.filtered(
            lambda m: m.move_type == 'in_invoice' and m.state == 'posted' and m.amount_residual > 0
        )
        if not invoices:
            raise UserError(_('No unpaid bills found. Please post the bill first.'))

        # Create payment
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_id.id,
            'amount': self.payment_amount,
            'journal_id': self.payment_journal_id.id,
            'date': self.payment_date or fields.Date.today(),
            'memo': self.payment_memo or _('Payment for %s') % self.purchase_order_id.name,
        })
        payment.action_post()

        # Reconcile payment with bills
        self._do_reconcile(payment.move_id)

        return self._refresh()

    def action_reconcile_all_outstanding(self):
        """Reconcile ALL outstanding payments with bill"""
        self.ensure_one()

        if not self.outstanding_debit_ids:
            raise UserError(_('No outstanding payments to reconcile.'))

        invoices = self.purchase_order_id.invoice_ids.filtered(
            lambda m: m.move_type == 'in_invoice' and m.state == 'posted' and m.amount_residual > 0
        )

        if not invoices:
            raise UserError(_('No unpaid bill to reconcile.'))

        # Get invoice payable lines
        invoice_lines = invoices.mapped('line_ids').filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )

        if invoice_lines and self.outstanding_debit_ids:
            try:
                (invoice_lines + self.outstanding_debit_ids).reconcile()
            except Exception as e:
                raise UserError(_('Reconciliation failed: %s') % str(e))

        return self._refresh()

    def action_reconcile_single_line(self, line_id):
        """Reconcile a single outstanding payment line with bill"""
        self.ensure_one()

        line = self.env['account.move.line'].browse(line_id)
        if not line.exists() or line.reconciled:
            raise UserError(_('Payment line not found or already reconciled.'))

        invoices = self.purchase_order_id.invoice_ids.filtered(
            lambda m: m.move_type == 'in_invoice' and m.state == 'posted' and m.amount_residual > 0
        )

        if not invoices:
            raise UserError(_('No unpaid bill to reconcile.'))

        # Get invoice payable lines
        invoice_lines = invoices.mapped('line_ids').filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )

        if invoice_lines:
            try:
                (invoice_lines + line).reconcile()
            except Exception as e:
                raise UserError(_('Reconciliation failed: %s') % str(e))

        return self._refresh()

    def _do_reconcile(self, payment_move):
        """Reconcile payment move with invoices"""
        invoices = self.purchase_order_id.invoice_ids.filtered(
            lambda m: m.move_type == 'in_invoice' and m.state == 'posted' and m.amount_residual > 0
        )

        # Payment creates debit on payable (positive residual)
        payment_lines = payment_move.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )

        for invoice in invoices:
            # Bill creates credit on payable (negative residual)
            invoice_lines = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
            )
            if payment_lines and invoice_lines:
                try:
                    (payment_lines + invoice_lines).reconcile()
                except Exception:
                    pass

    def action_done(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}

    def _refresh(self):
        """Refresh the wizard to show updated status"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quick Process'),
            'res_model': 'po.quick.process',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
