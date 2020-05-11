from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero


class Contract(models.Model):
    _inherit = 'hr.contract'

    wage = fields.Monetary(string='Total Salary')
    basic_db = fields.Monetary(related='x_basic_db')
    basic_non_db = fields.Monetary(related='x_basic_non_db')
    grade = fields.Selection(related='x_grade')
    scale_point = fields.Char(related='x_scale_point')
    pay_group = fields.Selection(related='x_pay_group')
