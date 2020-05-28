from odoo import api, fields, models, tools, exceptions, _
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import ValidationError


class Contract(models.Model):
    _inherit = 'hr.contract'

    def write(self, vals):
        res = super(Contract, self).write(vals)
        pending = res.employee_id.slip_ids.filtered(lambda r: r.state in ['draft', 'verify'])
        if pending:
            raise ValidationError("You cannot make changes to the record because a payroll is in progress for this employee.")
        return res

    def fetch_data_from_ros(self):
        # Method to fetch data from ROS
        return True


class Employee(models.Model):
    _inherit = 'hr.employee'

    def write(self, vals):
        res = super(Employee, self).write(vals)
        pending = res.slip_ids.filtered(lambda r: r.state in ['draft', 'verify'])
        if pending:
            raise ValidationError("You cannot make changes to the record because a payroll is in progress for this employee.")
        return res

    bank_account_no = fields.Char('Bank Account Number')
    joining_date = fields.Date('Joining Date')
    leaving_date = fields.Date('Leaving Date')
    remaining_leaves_offboarding_erpify = fields.Float('Leaves Balance on Off Boarding')

    def get_remaining_leaves_offboarding_erpify(self):
        if self.contract_id:
            total_allocations = self.env['hr.leave.allocation'].search([('employee_id', '=', self.id), ('state', '=', 'validate'),
                                                                        ('leave_type', '=', 'allocation'), ('holiday_status_id.allocation_type', 'in', ['fixed_allocation', 'fixed'])])
            current_year_allocations = self.env['hr.leave.allocation'].search([('employee_id', '=', self.id), ('allocation_period_start', '>=', self.contract_id.date_start),
                                                    ('state', '=', 'validate'), ('leave_type', '=', 'allocation'), ('holiday_status_id.allocation_type', 'in', ['fixed_allocation', 'fixed'])])
            leaves_till_leaving_date = self.env['hr.leave.allocation'].search([('employee_id', '=', self.id), ('state', '=', 'validate'), ('leave_type', '=', 'request'), ('holiday_status_id.allocation_type', 'in', ['fixed_allocation', 'fixed'])])
            total_allocations = sum(total_allocations.mapped('number_of_days')) if total_allocations else 0
            current_year_allocations = sum(current_year_allocations.mapped('number_of_days')) if current_year_allocations else 0
            leaves_till_leaving_date = sum(
                leaves_till_leaving_date.mapped('number_of_days')) if leaves_till_leaving_date else 0
            accrual_balance = (current_year_allocations / 52) * self.leaving_date.isocalendar()[1]
            self.remaining_leaves_offboarding_erpify = total_allocations - current_year_allocations + accrual_balance - leaves_till_leaving_date

    def initiate_termination(self):
        if len(self) == 1 and not self.leaving_date:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Register Departure/Termination'),
                'res_model': 'hr.departure.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_id': self.id},
                'views': [[False, 'form']]
            }


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    leaving_date = fields.Date('Leaving Date', required=True)
    departure_reason = fields.Selection([
        ('fired', 'Fired'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired'),
        ('died', 'Died'),
    ], string="Departure Reason", default="fired", required=True)

    def action_register_departure(self):
        super(HrDepartureWizard, self).action_register_departure()
        self.employee_id.leaving_date = self.leaving_date
        self.employee_id.get_remaining_leaves_offboarding_erpify()


class Allocation(models.Model):
    _inherit = 'hr.leave.allocation'

    allocation_period_start = fields.Date('Allocation for the period')
    allocation_period_end = fields.Date('Ending')


class LeaveReport(models.Model):
    _inherit = "hr.leave.report"

    allocation_period_start = fields.Date('Allocation for the period', readonly=True)
    allocation_period_end = fields.Date('Ending', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_report')

        self._cr.execute("""
                CREATE or REPLACE view hr_leave_report as (
                    SELECT row_number() over(ORDER BY leaves.employee_id) as id,
                    leaves.employee_id as employee_id, leaves.name as name,
                    leaves.number_of_days as number_of_days, leaves.leave_type as leave_type,
                    leaves.category_id as category_id, leaves.department_id as department_id,
                    leaves.holiday_status_id as holiday_status_id, leaves.state as state,
                    leaves.holiday_type as holiday_type, leaves.date_from as date_from,
                    leaves.date_to as date_to, leaves.payslip_status as payslip_status,
                    leaves.allocation_period_end as allocation_period_end, leaves.allocation_period_start as allocation_period_start
                    
                    from (select
                        allocation.employee_id as employee_id,
                        allocation.name as name,
                        allocation.number_of_days as number_of_days,
                        allocation.category_id as category_id,
                        allocation.department_id as department_id,
                        allocation.holiday_status_id as holiday_status_id,
                        allocation.state as state,
                        allocation.holiday_type,
                        null as date_from,
                        null as date_to,
                        FALSE as payslip_status,
                        'allocation' as leave_type,
                        allocation.allocation_period_start AS allocation_period_start,
                        allocation.allocation_period_end AS allocation_period_end
                    from hr_leave_allocation as allocation
                    union all select
                        request.employee_id as employee_id,
                        request.name as name,
                        (request.number_of_days * -1) as number_of_days,
                        request.category_id as category_id,
                        request.department_id as department_id,
                        request.holiday_status_id as holiday_status_id,
                        request.state as state,
                        request.holiday_type,
                        request.date_from as date_from,
                        request.date_to as date_to,
                        request.payslip_status as payslip_status,
                        'request' as leave_type
                    from hr_leave as request) leaves
                );
            """)

