import base64
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMoveProformaInvoice(models.Model):
    """Extends account.move with a downloadable pro forma invoice PDF.

    Layout: landscape A4, two identical copies side-by-side.
    BILL TO details are sourced from the insurance company linked to the
    eyekei.insurance.claim that references this invoice.
    """

    _inherit = "account.move"

    # ── Internal helpers ──────────────────────────────────────────────────

    def _proforma_fit_text(self, c, text, max_w, font, size, min_size=5):
        """Shrink font until text fits max_w; truncate with '…' as last resort."""
        while size >= min_size:
            c.setFont(font, size)
            if c.stringWidth(text, font, size) <= max_w:
                return size, text
            size -= 0.5
        while text and c.stringWidth(text + "…", font, min_size) > max_w:
            text = text[:-1]
        return min_size, text + "…"

    def _proforma_wrap_text(self, c, text, max_w, font, size):
        """Break text into lines that all fit within max_w."""
        c.setFont(font, size)
        words = (text or "").split()
        lines, current = [], ""
        for word in words:
            test = (current + " " + word).strip()
            if c.stringWidth(test, font, size) <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    def _get_claim_insurance_details(self):
        """Return insurance company details for BILL TO from linked claim.

        Traversal: account.move  ←invoice_id—  eyekei.insurance.claim
                                                     └→ insurance_company_id
        """
        claim = self.env["eyekei.insurance.claim"].search(
            [("invoice_id", "=", self.id)], limit=1
        )
        if not claim or not claim.insurance_company_id:
            return None
        ins = claim.insurance_company_id
        return {
            "name": ins.name or "",
            "company": ins.name or "",
            "street": (ins.address or "").split("\n")[0] if ins.address else "",
            "city": (
                (ins.address or "").split("\n")[1]
                if ins.address and "\n" in ins.address
                else ""
            ),
            "phone": ins.phone or "",
            "email": ins.email or "",
            "claim_no": claim.name or "",
            "member_no": claim.member_number or "",
            "scheme": claim.scheme_id.name if claim.scheme_id else "",
        }

    def download_proforma_invoice(self):
        """Trigger the QWeb PDF report for this prescription."""
        self.ensure_one()
        return self.env.ref(
            "eyekei_eyewear.action_report_proforma_invoice",
        ).report_action(self)


import csv
import json
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable

TWOPLACES = Decimal("0.01")


@dataclass(frozen=True)
class BundleRule:
    required: Dict[str, int]
    reward_product: str
    reward_discount_rate: Decimal


KITCHEN_STARTER_RULE = BundleRule(
    required={"PRODUCT_001": 3, "PRODUCT_002": 2},
    reward_product="PRODUCT_003",
    reward_discount_rate=Decimal("0.90"),
)


class SalesProcessingError(Exception):
    """Raised when the CSV is invalid or cannot be processed."""
    pass


def quantize_money(value: Decimal) -> Decimal:
    """Round a Decimal monetary value to 2 decimal places (Half-Up)."""
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def process_sales_order(csv_path: str | Path, rule: BundleRule = KITCHEN_STARTER_RULE) -> dict:
    """
    Process a CSV sales order file efficiently using O(n) streaming.
    """
    path = Path(csv_path)
    if not path.exists():
        raise SalesProcessingError(f"File not found: {csv_path}")

    # Aggregators
    required_counts = {p_id: 0 for p_id in rule.required}
    total_original_value = Decimal("0.00")
    reward_product_price = None

    try:
        with path.open(mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Validate headers
            expected_headers = {"product_id", "quantity", "unit_price"}
            if not expected_headers.issubset(set(reader.fieldnames or [])):
                raise SalesProcessingError(f"CSV missing required columns: {expected_headers}")

            for row in reader:
                try:
                    p_id = row["product_id"]
                    qty = int(row["quantity"])
                    u_price = Decimal(row["unit_price"])
                except (ValueError, TypeError):
                    continue  # Or raise SalesProcessingError for strict validation

                # 1. Update total original value
                total_original_value += qty * u_price

                # 2. Track quantities for bundle components
                if p_id in required_counts:
                    required_counts[p_id] += qty

                # 3. Capture reward product price (consistent across file)
                if p_id == rule.reward_product:
                    reward_product_price = u_price
        # Validation: Ensure we found the reward product to determine discount value
        if reward_product_price is None:
            raise SalesProcessingError(
                f"Reward product {rule.reward_product} not found in file. Price cannot be determined."
            )
        # 4. Greedy Bundle Detection
        # Calculate how many bundles are possible for each required item
        possible_bundles = [
            required_counts[p_id] // req_qty
            for p_id, req_qty in rule.required.items()
        ]
        bundle_count = min(possible_bundles) if possible_bundles else 0

        # 5. Financial Calculations
        # Reward value = (Price * Discount Rate) * Bundle Count
        reward_value = quantize_money(
            reward_product_price * rule.reward_discount_rate * bundle_count
        )
        final_total = quantize_money(total_original_value - reward_value)

        return {
            "total_original_value": str(quantize_money(total_original_value)),
            "bundle_count": bundle_count,
            "reward_value": str(reward_value),
            "final_total": str(final_total)
        }

    except Exception as e:
        if not isinstance(e, SalesProcessingError):
            raise SalesProcessingError(f"Unexpected error during processing: {e}")
        raise


def main(argv: Iterable[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1:
        print("Usage: python solution/sales_processor.py <csv_path>", file=sys.stderr)
        return 1

    csv_path = args[0]

    try:
        result = process_sales_order(csv_path)
        print(json.dumps(result, indent=2))
    except SalesProcessingError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Fatal Error: {exc}", file=sys.stderr)
        return 4

    return 0


if __name__ == "__main__":
    sys.exit(main())