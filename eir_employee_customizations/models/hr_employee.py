from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero


class Contract(models.Model):
    _inherit = 'hr.contract'

    wage = fields.Monetary()
    basic_db = fields.Monetary()
    basic_non_db = fields.Monetary()
    grade = fields.Selection([('1', '1'), ('appt','APPT'), ('cot1', 'COT1'), ('csr', 'CSR'), ('ctl', 'CTL'), ('flm', 'FLM'), ('meteor', 'METEOR'),
                    ('nmct', 'NMCT'), ('pc', 'PC'), ('pcmetr', 'PCMETR'), ('pcni', 'PCNI'), ('pcuk', 'PCUK'), ('pczex', 'PCZEX'),
                    ('pdtm', 'PDTM'), ('ptcsr', 'PTCSR'), ('som', 'S.O.M'), ('tex8', 'TEX8'), ('to', 'TO'), ('ttl', 'TTL')])
    scale_point = fields.Char()
    pay_group = fields.Char()
