from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class Timesheets(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _get_ordinary_type(self):
        default = self.env['timesheet.allowances.category.erpify'].search([('select_by_default', '=', True)], limit=1).id
        if default:
            return default
        else:
            return False

    tz = fields.Selection(related='employee_id.tz', string='Time Zone', readonly=True, store=False)
    start = fields.Float(string="From")
    end = fields.Float(string="To")
    name = fields.Char(string='Appropriation Code')
    employee_shift_erpify = fields.Many2one('resource.calender')
    timesheet_submission_erpify_id = fields.Many2one('timesheet.submission.erpify')
    type_id_erpify = fields.Many2one('timesheet.allowances.category.erpify', string='Type', default=_get_ordinary_type)

    @api.model
    def create(self, vals):
        employee = self.env.user.employee_id
        vals.update({'project_id': employee.project_id_erpify.id,
                     'account_id': employee.project_id_erpify.analytic_account_id.id})
        result = super(Timesheets, self).create(vals)
        if result.employee_id:
            result.employee_shift_erpify = result.employee_id.resource_calendar_id.id
        return result

    @api.onchange('end')
    def calculate_duration(self):
        if self.start and self.end:
            self.unit_amount = self.end - self.start


class TimeSheetSubmission(models.Model):
    _name = 'timesheet.submission.erpify'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Timesheets Request'

    name = fields.Char(compute='_get_record_name', store=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    time_in_lieu = fields.Float(default=50.0)
    timesheet_ids = fields.One2many('account.analytic.line', 'timesheet_submission_erpify_id')
    state = fields.Selection([('draft', 'Draft'), ('submit', 'Submitted'), ('approved', 'Approved'),
                              ('cancel', 'Cancelled')], default='draft', string='Status')
    approval_matrix = fields.One2many('timesheet.approval.matrix', 'timesheet_submission_id')
    submission_date = fields.Datetime()

    @api.depends('employee_id', 'start_date', 'end_date')
    def _get_record_name(self):
        for r in self:
            r.name = r.employee_id.name + ': ' + r.start_date.strftime(DATE_FORMAT) + ' to ' + r.end_date.strftime(DATE_FORMAT)

    @api.constrains('time_in_lieu')
    def check_time_in_lieu(self):
        if self.time_in_lieu > 50:
            raise ValidationError(_('Time In Lieu cannot be greater than 50%'))
        elif self.time_in_lieu < 0:
            raise ValidationError(_('Time In Lieu cannot be less than 0%'))

    @api.constrains('start_date', 'end_date')
    def _onchange_start_date_or_end_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(_('The end date should be greater than the starting date.'))

    def fetch_timesheets(self):
        if self.start_date and self.end_date and self.employee_id:
            timesheets = self.env['account.analytic.line'].search([('employee_id', '=', self.employee_id.id), ('date', '>=', self.start_date),
                                                      ('date', '<=', self.end_date), ('timesheet_submission_erpify_id', '=', False)]).ids
            if timesheets:
                self.timesheet_ids = [(6, 0, timesheets)]

    def cancel(self):
        self.state = 'cancel'
        self.timesheet_ids.unlink()

    def approve_reject(self):
        return {
            'name': _('Approve or Reject the timesheets'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'popup.wizard.timesheet',
            'target': 'new',
            'context': dict(
                self.env.context,
                default_user_id=self.env.user.id,
                default_timesheet_submission_id=self.id,
            ),
        }

    def submit_request(self):
        self.fetch_timesheets()
        self.submission_date = datetime.now()
        self.state = 'submit'


class ApprovalMatrixTimesheet(models.Model):
    _name = 'timesheet.approval.matrix'
    _description = 'Timesheet Approval Matrix'

    user_id = fields.Many2one('res.users', 'Approver')
    checked_at = fields.Datetime()
    status = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected')])
    comments = fields.Text()
    timesheet_submission_id = fields.Many2one('timesheet.submission.erpify')


class Wizard(models.TransientModel):
    _name = 'popup.wizard.timesheet'

    comments = fields.Text('Comments')
    user_id = fields.Many2one('res.users')
    timesheet_submission_id = fields.Many2one('timesheet.submission.erpify')
    status = fields.Selection([('approve', 'Approve'), ('reject', 'Reject')], string='Action to Perform?')

    def proceed(self):
        self.timesheet_submission_id.approval_matrix.create({
            'user_id': self.user_id.id,
            'checked_at': datetime.now(),
            'status': self.status,
            'comments': self.comments,
            'timesheet_submission_id': self.timesheet_submission_id.id,
        })


class Employee(models.Model):
    _inherit = 'hr.employee'

    project_id_erpify = fields.Many2one('project.project', 'Timesheet Project')