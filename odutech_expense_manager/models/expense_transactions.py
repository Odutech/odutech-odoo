from odoo import models, fields, api


class ExpenseTransaction(models.Model):
    _name = 'expense.transaction'
    _description = 'Transaction Records'

    transaction_code = fields.Char(string="Transaction Code", required=True,readonly=True)
    date_creation = fields.Datetime(string="Date of Creation", default=fields.Datetime.now,readonly=True)
    amount = fields.Float(string="Amount")
    type = fields.Selection([
        ('income', 'Income'),
        ('saving', 'Saving'),
        ('expense', 'Expense')
    ], string="Type", required=True,readonly=True)

    category_id = fields.Many2one('expense.category', string="Linked Category",readonly=True)
    user_id = fields.Many2one('expense.user', string="Linked User",readonly=True)
    currency_id = fields.Many2one('res.currency',string="Currency",readonly=True,related="user_id.currency_id")
    account_id = fields.Many2one('expense.account', string="Linked Account",readonly=True)