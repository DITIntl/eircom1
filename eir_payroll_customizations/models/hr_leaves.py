from odoo import api, fields, models, tools, exceptions, _
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import ValidationError


class Leaves(models.Model):
    _inherit = 'hr.leave'

    def write(self, vals):
        res = super(Leaves, self).write(vals)
        pending = self.employee_id.slip_ids.filtered(lambda r: r.state in ['draft', 'verify'])
        if pending:
            raise ValidationError("You cannot make changes to the record because a payroll is in progress for this employee.")
        return res


class TimesheetSubmission(models.Model):
    _inherit = 'timesheet.submission.erpify'

    def approve_reject(self):
        pending = self.employee_id.slip_ids.filtered(lambda r: r.state in ['draft', 'verify'])
        if pending:
            raise ValidationError(
                "You cannot make changes to the record because a payroll is in progress for this employee.")
        return super(TimesheetSubmission, self).approve_reject()