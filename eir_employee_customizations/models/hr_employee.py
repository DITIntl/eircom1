from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero


class Contract(models.Model):
    _inherit = 'hr.contract'

    wage = fields.Monetary(string='Total Salary')

