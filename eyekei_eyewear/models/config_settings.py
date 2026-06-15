# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    """EYEKEI Configuration Settings"""
    _inherit = 'res.config.settings'

    # eTIMS Integration
    etims_enabled = fields.Boolean(string='Enable eTIMS', config_parameter='eyekei.etims_enabled')
    etims_api_url = fields.Char(string='eTIMS API URL', config_parameter='eyekei.etims_api_url')
    etims_api_key = fields.Char(string='eTIMS API Key', config_parameter='eyekei.etims_api_key', password=True)
    etims_pin = fields.Char(string='eTIMS PIN', config_parameter='eyekei.etims_pin', password=True)
    etims_test_mode = fields.Boolean(string='eTIMS Test Mode', config_parameter='eyekei.etims_test_mode', default=True)

    # SMS Gateway
    sms_enabled = fields.Boolean(string='Enable SMS', config_parameter='eyekei.sms_enabled')
    sms_provider = fields.Selection([
        ('twilio', 'Twilio'),
        ('africastalking', 'Africa\'s Talking'),
        ('custom', 'Custom'),
    ], string='SMS Provider', config_parameter='eyekei.sms_provider')
    sms_api_key = fields.Char(string='SMS API Key', config_parameter='eyekei.sms_api_key', password=True)
    sms_sender_id = fields.Char(string='SMS Sender ID', config_parameter='eyekei.sms_sender_id')

    # Patient Settings
    patient_id_prefix = fields.Char(string='Patient ID Prefix', config_parameter='eyekei.patient_id_prefix', default='EYE')
    patient_id_padding = fields.Integer(string='Patient ID Padding', config_parameter='eyekei.patient_id_padding', default=6)
    enable_self_registration = fields.Boolean(string='Enable Self-Registration', config_parameter='eyekei.enable_self_registration', default=True)

    # Clinical Settings
    lens_adaptation_days = fields.Integer(string='Lens Adaptation Period', config_parameter='eyekei.lens_adaptation_days', default=30)
    frame_warranty_months = fields.Integer(string='Frame Warranty', config_parameter='eyekei.frame_warranty_months', default=6)
    max_remake_percentage = fields.Float(string='Max Remake %', config_parameter='eyekei.max_remake_percentage', default=3.0)

    # Insurance Settings
    insurance_validity_days = fields.Integer(string='Insurance Validity', config_parameter='eyekei.insurance_validity_days', default=30)

    # Lab Settings
    job_priority = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('express', 'Express'),
    ], string='Default Job Priority', config_parameter='eyekei.default_job_priority', default='normal')
    urgent_job_surcharge = fields.Float(string='Urgent Surcharge %', config_parameter='eyekei.urgent_surcharge', default=20.0)
    enable_external_lab = fields.Boolean(string='Enable External Lab', config_parameter='eyekei.enable_external_lab', default=True)
