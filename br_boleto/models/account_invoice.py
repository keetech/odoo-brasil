# -*- coding: utf-8 -*-
# © 2016 Alessandro Fernandes Martini, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from odoo import api, models, fields
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    boleto = fields.Boolean(string='Boleto Bancário?', compute='_check_payment_mode', store=False)

    @api.depends('payment_mode_id')
    def _check_payment_mode(self):
        for record in self:
            if record.payment_mode_id.payment_method == 'boleto':
                record.boleto = True
            else:
                record.boleto = False

    @api.multi
    def send_email_boleto_queue(self):
        mail = self.env.user.company_id.boleto_email_tmpl
        if not mail:
            raise UserError('Modelo de email padrão não configurado')

        attachment_obj = self.env['ir.attachment']
        for item in self:

            atts = []
            self = self.with_context({
                'origin_model': 'account.invoice',
                'active_ids': [item.id],
            })
            boleto, fmt = self.env['ir.actions.report'].render_report(
                [item.id], 'br_boleto.report.print', {'report_type': u'pdf'})

            if boleto:
                name = "boleto-%s-%s.pdf" % (
                    item.number, item.partner_id.commercial_partner_id.name)
                boleto_id = attachment_obj.create(dict(
                    name=name,
                    datas_fname=name,
                    datas=base64.b64encode(boleto),
                    mimetype='application/pdf',
                    res_model='account.invoice',
                    res_id=item.id,
                ))
                atts.append(boleto_id.id)

            values = {
                "attachment_ids": atts + mail.attachment_ids.ids
            }
            mail.send_mail(item.id, email_values=values)

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        error = ''
        for item in self:
            if item.payment_mode_id and item.payment_mode_id.boleto_type != '':
                if not item.company_id.partner_id.legal_name:
                    error += u'Empresa - Razão Social\n'
                if not item.company_id.cnpj_cpf:
                    error += u'Empresa - CNPJ\n'
                if not item.company_id.district:
                    error += u'Empresa - Bairro\n'
                if not item.company_id.zip:
                    error += u'Empresa - CEP\n'
                if not item.company_id.city_id.name:
                    error += u'Empresa - Cidade\n'
                if not item.company_id.street:
                    error += u'Empresa - Logradouro\n'
                if not item.company_id.number:
                    error += u'Empresa - Número\n'
                if not item.company_id.state_id.code:
                    error += u'Empresa - Estado\n'

                if not item.commercial_partner_id.name:
                    error += u'Cliente - Nome\n'
                if item.commercial_partner_id.is_company and \
                   not item.commercial_partner_id.legal_name:
                    error += u'Cliente - Razão Social\n'
                if not item.commercial_partner_id.cnpj_cpf:
                    error += u'Cliente - CNPJ/CPF \n'
                if not item.commercial_partner_id.district:
                    error += u'Cliente - Bairro\n'
                if not item.commercial_partner_id.zip:
                    error += u'Cliente - CEP\n'
                if not item.commercial_partner_id.city_id.name:
                    error += u'Cliente - Cidade\n'
                if not item.commercial_partner_id.street:
                    error += u'Cliente - Logradouro\n'
                if not item.commercial_partner_id.number:
                    error += u'Cliente - Número\n'
                if not item.commercial_partner_id.state_id.code:
                    error += u'Cliente - Estado\n'

                if item.number and len(item.number) > 12:
                    error += u'Numeração da fatura deve ser menor que 12 ' + \
                        'caracteres quando usado boleto\n'

                if len(error) > 0:
                    raise UserError(u"""Ação Bloqueada!
Para prosseguir é necessário preencher os seguintes campos:\n""" + error)
        return res

    @api.multi
    def action_register_boleto(self):
        if self.payment_mode_id.payment_method != 'boleto':
            raise UserError(
                u'O método de pagamento definido é diferente de boleto!')
        if self.state in ('draft', 'cancel'):
            raise UserError(
                u'Fatura provisória ou cancelada não permite emitir boleto')
        self = self.with_context({'origin_model': 'account.invoice'})
        return self.env.ref(
            'br_boleto.action_boleto_account_invoice').report_action(self)
