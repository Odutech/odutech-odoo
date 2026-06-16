from odoo import models, fields, api

class ExpenseCategory(models.Model):
    _name = 'expense.category'
    _description = 'Expense Category'
    _order = 'sequence'

    name = fields.Char(string="Category Name", required=True,readonly=True)
    sequence = fields.Integer(string="Sequence", default=0,readonly=True)
    icon = fields.Binary(string="Icon",readonly=True)
    user_id = fields.Many2one('expense.user', string="Linked User",readonly=True)
    total_amount = fields.Float(string="Total Amount Transacted", compute="_compute_total_amount", store=True,readonly=True)
    transaction_ids = fields.One2many('expense.transaction', 'category_id',readonly=True)
    currency_id = fields.Many2one('res.currency',string="Currency",readonly=True,related="user_id.currency_id")
    income_percentage_deduct = fields.Float(string="Income Percentage Deduct",readonly=True)

    @api.depends('transaction_ids.amount')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.transaction_ids.mapped('amount'))
