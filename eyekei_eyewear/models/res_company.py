import base64
from io import BytesIO

import qrcode

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    registration_qr_code = fields.Binary("Registration QR Code", readonly=True)
    registration_qr_filename = fields.Char("QR Filename", default="registration_qr.png")

    def action_generate_registration_qr(self):
        """Generate QR Code for Patient Self-Registration"""
        self.ensure_one()

        url = "{}/eyekei/register/{}".format(
            self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            self.id,
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue())

        self.write({
            'registration_qr_code': qr_code,
            'registration_qr_filename': "QR_{}.png".format(self.name.replace(' ', '_')),
        })

        # Return download URL dynamically — no static act_url record needed
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/image/res.company/{self.id}/registration_qr_code/{self.registration_qr_filename}',
            'target': 'new',
        }

    def action_download_qr(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/image/res.company/{self.id}/registration_qr_code/{self.registration_qr_filename}',
            'target': 'new',
        }
