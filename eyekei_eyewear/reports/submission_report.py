from odoo import models, api


class SubmissionBatchReport(models.AbstractModel):
    _name = "report.eyekei_eyewear.submission_batch_report"
    _description = "Insurance Submission Batch Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["eyekei.submission.batch"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "eyekei.submission.batch",
            "docs": docs,
            "company": self.env.company,
        }
