from odoo import models, fields, api

class ExpenseAccount(models.Model):
    _name = 'expense.account'
    _description = 'Financial Account'

    name = fields.Char(string="Account Name", required=True,readonly=True)
    account_number = fields.Char(string="Account Number", required=True,readonly=True)
    total_available = fields.Float(string="Total Amount Available",readonly=True)
    user_id = fields.Many2one('expense.user', string="Linked User",readonly=True)
    currency_id = fields.Many2one('res.currency',string="Currency",readonly=True,related="user_id.currency_id")
    type = fields.Selection([
        ('income', 'Income Account'),
        ('expense', 'Expense Account'),
        ('saving', 'Saving Account')
    ], string="Account Type", required=True,readonly=True)



