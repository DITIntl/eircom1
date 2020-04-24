from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class Allowances(models.Model):
    _name = 'timesheet.allowances.category.erpify'
    _description = 'Timesheet Allowances Categories'

    name = fields.Char(required=True)
    start = fields.Float('Start')
    end = fields.Float('End')
    active = fields.Boolean('Active', default=True, tracking=True)
    show_in_timesheet = fields.Boolean('Show while entering timesheets?', default=True)


