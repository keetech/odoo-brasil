# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.multi
    @api.depends('debit', 'credit', 'user_type_id', 'amount_residual')
    def _compute_payment_value(self):
        for item in self:
            item.payment_value = item.debit \
                if item.user_type_id.type == 'receivable' else item.credit * -1
    payment_value = fields.Float(
        string="Valor", compute=_compute_payment_value)

    @api.multi
    def action_register_boleto(self):
        if self.state in ('draft', 'cancel'):
            raise UserError(
                'Fatura provisória ou cancelada não permite emitir boleto')
        self = self.with_context({'origin_model': 'account.invoice'})
        return self.env['report'].get_action(self.id, 'br_boleto.report.print')

    @api.multi
    def action_register_payment(self):
        dummy, act_id = self.env['ir.model.data'].get_object_reference(
            'account', 'action_account_invoice_payment')
        vals = self.env['ir.actions.act_window'].browse(act_id).read()[0]
        vals['context'] = {'default_amount': self.debit or self.credit,
                           'default_partner_type': 'supplier',
                           'default_partner_id': self.partner_id.id,
                           'default_communication': self.name,
                           'default_payment_type': 'outbound'}
        return vals
