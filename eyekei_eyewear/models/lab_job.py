from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class LabJob(models.Model):
    _name = "eyekei.lab.job"
    _description = "Lab Job Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char("Job ID", readonly=True, default="New", tracking=True)
    visit_id = fields.Many2one(
        "eyekei.patient.visit", "Visit", required=True, tracking=True,
    )
    patient_id = fields.Many2one(
        "res.partner",
        "Patient",
        related="visit_id.patient_id",
        store=True,
        tracking=True,
    )
    sent_to_lab_date = fields.Datetime("Sent To Lab Date", tracking=True)
    branch_id = fields.Many2one("res.company", "Branch", required=True, tracking=True)

    # Job status workflow
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("received", "Received by Lab"),
            ("waiting_lens", "Waiting for Lens"),
            ("in_production", "In Production"),
            ("qc", "Quality Control"),
            ("ready", "Ready for Dispatch"),
            ("dispatched", "Dispatched to Clinic"),
            ("delivered", "Delivered to Clinic"),
            ("remake", "Remake Required"),
        ],
        default="draft",
        tracking=True,
    )
    priority = fields.Selection(
        [
            ("normal", "Normal"),
            ("urgent", "Urgent"),
            ("express", "Express"),
        ],
        string="Priority",
        default="normal",
        tracking=True,
    )

    # Job details
    prescription_id = fields.Many2one(
        "eyekei.prescription", "Prescription", tracking=True,
    )
    frame_product_id = fields.Many2one(
        "product.product",
        "Frame (Product)",
        domain="[('optical_type', '=', 'frame')]",
        tracking=True,
    )

    # Lens assignment
    lens_product_id = fields.Many2one(
        "product.product",
        "Lens (Product)",
        domain="[('optical_type', '=', 'lens')]",
        tracking=True,
    )
    lens_batch_number = fields.Char("Lens Batch Number", tracking=True)

    # Stock reservation (link to stock.move)
    stock_move_ids = fields.One2many(
        "stock.move", "lab_job_id", "Stock Moves", tracking=True,
    )
    reservation_state = fields.Selection(
        [
            ("not_reserved", "Not Reserved"),
            ("reserved", "Stock Reserved"),
            ("consumed", "Stock Consumed"),
            ("returned", "Stock Returned"),
        ],
        default="not_reserved",
        tracking=True,
    )

    # Source tracking
    source_type = fields.Selection(
        [
            ("central", "Central Lab"),
            ("clinic_stock", "Clinic Stock"),
            ("external", "External Vendor"),
        ],
        required=True,
        tracking=True,
    )
    external_vendor_id = fields.Many2one(
        "res.partner",
        string="External Vendor",
        domain="[('is_optical_vendor', '=', True), ('active', '=', True)]",
        help="Select an external optical lab/vendor",
        tracking=True,
    )
    external_cost = fields.Float("External Glazing Cost", tracking=True)
    purchase_order_id = fields.Many2one("purchase.order", "Purchase Order", tracking=True)

    # Timestamps
    sent_to_lab_date = fields.Datetime("Sent to Lab Date", tracking=True)
    received_date = fields.Datetime("Received Date", tracking=True)
    production_start = fields.Datetime("Production Start", tracking=True)
    production_end = fields.Datetime("Production End", tracking=True)
    dispatch_date = fields.Datetime("Dispatch Date", tracking=True)
    delivery_date = fields.Datetime("Delivery Date", tracking=True)
    lens_product_id_od = fields.Many2one(
        "product.product",
        "Lens Model (L)",
        domain="[('optical_type', '=', 'lens')]",
        tracking=True,
    )
    lens_type_od = fields.Many2one("eyekei.lens.type.categorization", string="Lens Type (L)",
                                domain=[("lens_categorization", "=", "lens_type")],
                                store=True,
                                tracking=True)
    lens_index_od = fields.Many2one("eyekei.lens.type.categorization", string="Lens Index (L)",
                                 domain=[("lens_categorization", "=", "lens_index")],
                                tracking=True)

    lens_coating_od = fields.Many2one("eyekei.lens.type.categorization", string="Lens Tint (L) ",
                                   domain=[("lens_categorization", "=", "lens_coating")],
                                   store=True,

                                   tracking=True)
    lens_type_os = fields.Many2one("eyekei.lens.type.categorization", string="Lens Type (R)",
                                   domain=[("lens_categorization", "=", "lens_type")],
                                   store=True,
                                   tracking=True)
    lens_index_os = fields.Many2one("eyekei.lens.type.categorization", string="Lens Index (R)",
                                    domain=[("lens_categorization", "=", "lens_index")],
                                    tracking=True)

    lens_coating_os = fields.Many2one("eyekei.lens.type.categorization", string="Lens Tint (R)",
                                      domain=[("lens_categorization", "=", "lens_coating")],
                                      store=True,

                                      tracking=True)
    lens_product_id_os = fields.Many2one(
        "product.product",
        "Lens Model (R)",
        domain="[('optical_type', '=', 'lens')]",
        tracking=True,
    )
    # Right Eye (OD)
    od_sph = fields.Float("SPH", tracking=True)
    od_cyl = fields.Float("CYL", tracking=True)
    od_axis = fields.Integer("AXIS", tracking=True)
    od_add = fields.Float("ADD", tracking=True)
    od_va = fields.Char("V/A", tracking=True)

    # Left Eye (OS)
    os_sph = fields.Float("SPH", tracking=True)
    os_cyl = fields.Float("CYL", tracking=True)
    os_axis = fields.Integer("AXIS", tracking=True)
    os_add = fields.Float("ADD", tracking=True)
    os_va = fields.Char("V/A", tracking=True)

    # QC
    qc_passed = fields.Boolean("QC Passed", tracking=True)
    qc_notes = fields.Text("QC Notes", tracking=True)
    qc_checked_by = fields.Many2one("res.users", "QC Checked By", tracking=True)

    # Technician tracking
    technician_id = fields.Many2one("res.users", "Assigned Technician", tracking=True)

    # Remake tracking
    is_remake = fields.Boolean("Is Remake", tracking=True)
    original_job_id = fields.Many2one("eyekei.lab.job", "Original Job", tracking=True)

    # Computed fields for performance
    turnaround_hours = fields.Float(
        "Turnaround Time (Hours)",
        compute="_compute_turnaround",
        store=True,
    )

    external_cost_breakdown = fields.Text("External Cost Details", tracking=True)
    transport_cost = fields.Float("Transport Cost", tracking=True)
    total_external_cost = fields.Float(
        "Total External Cost",
        compute="_compute_external_cost",
        store=True,
    )

    @api.depends("external_cost", "transport_cost")
    def _compute_external_cost(self):
        for job in self:
            job.total_external_cost = (job.external_cost or 0) + (
                job.transport_cost or 0
            )

    @api.onchange("external_vendor_id")
    def _onchange_external_vendor(self):
        """Check if vendor requires approval"""
        if self.external_vendor_id and self.external_vendor_id.requires_approval:
            return {
                "warning": {
                    "title": _("Approval Required"),
                    "message": _(
                        "This vendor requires manager approval. Please ensure proper authorization before proceeding.",
                    ),
                },
            }
        return None

    def action_mark_vendor_complaint(self):
        """Quick action to register a complaint against vendor for this job"""
        self.ensure_one()
        return {
            "name": _("Register Vendor Complaint"),
            "type": "ir.actions.act_window",
            "res_model": "eyekei.remake.order",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_original_visit_id": self.visit_id.id,
                "default_remake_type": "manufacturer_defect",
                "default_complaint_type": _("Quality issue with external lab: %s")
                % self.external_vendor_id.name,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("eyekei.lab.job")
        return super().create(vals_list)

    @api.depends("production_start", "production_end")
    def _compute_turnaround(self):
        for job in self:
            if job.production_start and job.production_end:
                delta = job.production_end - job.production_start
                job.turnaround_hours = delta.total_seconds() / 3600
            else:
                job.turnaround_hours = 0

    def action_receive_job(self):
        self.write(
            {
                "state": "received",
                "received_date": fields.Datetime.now(),
                # "technician_id": self.env.user.id,
            },
        )
        # Check lens availability
        # self._check_lens_availability()

    def _check_lens_availability(self):
        """Auto-check lens stock based on prescription"""
        self.ensure_one()
        prescription = self.prescription_id
        if not prescription:
            return

        # Find matching lens in inventory
        domain = [
            ("lens_type", "=", prescription.lens_type),
            ("quantity_available", ">", 0),
        ]
        if prescription.lens_index:
            domain.append(("index", "=", prescription.lens_index))

        available_lens = self.env["product.product"].search(domain, limit=1)
        if available_lens:
            self.lens_product_id = available_lens.id
            self.state = "in_production"
            # Reserve stock
            available_lens._reserve_stock(1, self.name)
        else:
            self.state = "waiting_lens"

    def action_qc_pass(self):
        self.write(
            {"state": "qc", "qc_passed": True, "qc_checked_by": self.env.user.id},
        )

    def action_ready_for_dispatch(self):
        self.write({"state": "ready", "production_end": fields.Datetime.now()})

    def action_dispatch(self):
        self.write({"state": "dispatched", "dispatch_date": fields.Datetime.now()})
        # Notify clinic
        self.visit_id.state = "lab_ready"

    def action_confirm_delivery(self):
        self.write({"state": "delivered", "delivery_date": fields.Datetime.now()})
        self.visit_id.action_lab_ready()

    def _get_available_qty(self, product, location):
        """Get available quantity (on hand - reserved) for product in location."""
        self.ensure_one()

        # Use Odoo's standard quant calculation
        quants = self.env["stock.quant"].search(
            [
                ("product_id", "=", product.id),
                ("location_id", "=", location.id),
            ],
        )

        # Available = quantity - reserved_quantity
        return sum(
            quant.quantity - quant.reserved_quantity for quant in quants
        )

    def action_reserve_stock(self):
        """Reserve frame and lens from inventory using standard stock moves.

        Validates available quantity before reservation. If insufficient stock,
        raises error asking user to create a purchase request.
        """
        self.ensure_one()

        # Determine source location based on source_type
        if self.source_type == "clinic_stock":
            source_location = self.env["stock.location"].search(
                [
                    ("branch_id", "=", self.branch_id.id),
                    ("location_type", "=", "clinic_stock"),
                    ("usage", "=", "internal"),
                ],
                limit=1,
            )
        else:
            source_location = self.env["stock.location"].search(
                [("location_type", "=", "central_lab"), ("usage", "=", "internal")],
                limit=1,
            )

        if not source_location:
            raise ValidationError(_("No valid stock location found for this job"))

        # Destination is the lab/production location
        dest_location = (
            self.env["stock.location"].search(
                [
                    ("usage", "=", "production"),
                    ("company_id", "=", self.env.company.id),
                ],
                limit=1,
            )
            or source_location
        )  # Fallback

        # Check stock availability for all products before creating any moves
        insufficient_products = []
        products_to_reserve = []

        # Check Frame availability
        if self.frame_product_id:
            frame_qty = self._get_available_qty(self.frame_product_id, source_location)
            if frame_qty <= 0:
                insufficient_products.append(
                    {
                        "product": self.frame_product_id,
                        "required": 1,
                        "available": frame_qty,
                    },
                )
            else:
                products_to_reserve.append(
                    {
                        "product": self.frame_product_id,
                        "qty": 1,
                        "name_suffix": "Frame",
                    },
                )

        # Check Lens availability
        if self.lens_product_id:
            lens_qty = self._get_available_qty(self.lens_product_id, source_location)
            if lens_qty <= 0:
                insufficient_products.append(
                    {
                        "product": self.lens_product_id,
                        "required": 1,
                        "available": lens_qty,
                    },
                )
            else:
                products_to_reserve.append(
                    {
                        "product": self.lens_product_id,
                        "qty": 1,
                        "name_suffix": "Lens",
                    },
                )

        # If any products have insufficient stock, raise error
        if insufficient_products:
            product_details = "\n".join(
                [
                    f"• {p['product'].name} (Required: {p['required']}, Available: {p['available']:.2f})"
                    for p in insufficient_products
                ],
            )

            error_msg = _(
                "Insufficient stock for the following products in location '%(location)s':\n"
                "%(products)s\n\n"
                "Please create a Purchase Request to procure the required items,\n"
                "or select alternative products that are in stock.",
            ) % {
                "location": source_location.display_name,
                "products": product_details,
            }

            raise UserError(error_msg)

        # All products available - proceed with reservation
        moves = self.env["stock.move"]

        for item in products_to_reserve:
            product = item["product"]
            move = self.env["stock.move"].create(
                {
                    "reference": _("Lab Job %s - %s") % (self.name, item["name_suffix"]),
                    "product_id": product.id,
                    "product_uom_qty": item["qty"],
                    "product_uom": product.uom_id.id,
                    "location_id": source_location.id,
                    "location_dest_id": dest_location.id,
                    "origin": self.name,
                    "lab_job_id": self.id,
                    "state": "draft",  # Will be confirmed when production starts
                },
            )
            moves += move

        self.reservation_state = "reserved"

        # Create picking for visualization
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "internal"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )

        if picking_type and moves:
            stock_picking = self.env["stock.picking"].create(
                {
                    "picking_type_id": picking_type.id,
                    "location_id": source_location.id,
                    "location_dest_id": dest_location.id,
                    "origin": self.name,
                    "move_ids": [(6, 0, moves.ids)],
                },
            )
            stock_picking.action_confirm()
            stock_picking.button_validate()
        return self.write(
            {
                "state": "in_production",
                "production_start": fields.Datetime.now(),
            },
        )

    def action_start_production(self):
        """Confirm stock moves when production starts"""
        self.ensure_one()
        self.action_reserve_stock()  # Ensure stock is reserved before starting production
        # self.write(
        #     {"state": "in_production", "production_start": fields.Datetime.now()},
        # )

        # # Confirm and do stock moves
        # moves = self.env["stock.move"].search([("lab_job_id", "=", self.id)])
        # for move in moves:
        #     move._action_confirm()
        #     move._action_assign()
        #     # Immediate transfer for lab consumption
        #     move.quantity_done = move.product_uom_qty
        #     move._action_done()

        # self.reservation_state = "consumed"

    def action_sent_for_qc(self):
        self.ensure_one()
        self.write(
            {
                "state": "qc",
                "qc_passed": False,
            },
        )

    def action_remake_return_stock(self):
        """Return consumed stock for remake (reverse moves)"""
        self.ensure_one()
        moves = self.env["stock.move"].search([("lab_job_id", "=", self.id)])

        for move in moves:
            # Create return picking
            return_wizard = (
                self.env["stock.return.picking"]
                .with_context(
                    active_id=move.picking_id.id,
                    active_model="stock.picking",
                )
                .create({})
            )
            return_wizard.product_return_moves.write({"quantity": 1, "to_refund": True})
            return_wizard._create_returns()

        self.reservation_state = "returned"

    def action_lens_not_available(self):
        """Manually mark job as waiting for lens when stock is unavailable"""
        self.ensure_one()
        self.write(
            {
                "state": "waiting_lens",
            },
        )
        # Post a message so there's an audit trail
        self.message_post(
            body=_("Lens marked as unavailable. Job is waiting for lens stock."),
            message_type="notification",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Waiting for Lens"),
                "message": _("Job %s is now waiting for lens stock.") % self.name,
                "type": "warning",
                "sticky": False,
            },
        }

    def action_lens_arrived(self):
        """Mark lens as arrived and move job into production"""
        self.ensure_one()
        if not self.lens_product_id:
            raise UserError(
                _("Please assign a lens product before marking it as arrived."),
            )

        self.write(
            {
                "state": "in_production",
                "production_start": fields.Datetime.now(),
            },
        )

        # Reserve the lens stock now that it has arrived
        self.action_reserve_stock()

        self.message_post(
            body=_("Lens arrived. Job moved to In Production."),
            message_type="notification",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Lens Arrived"),
                "message": _("Job %s is now in production.") % self.name,
                "type": "success",
                "sticky": False,
            },
        }

    def action_qc_fail(self):
        self.ensure_one()
        self.write(
            {
                "state": "in_production",
                "qc_passed": False,
                "qc_checked_by": self.env.user.id,
            },
        )
        self.message_post(
            body=_("QC failed. Job requires rework."),
            message_type="notification",
        )

    def action_assign_lens(self):
        """Assign lens product and deduct from stock"""
        self.ensure_one()
        if not self.lens_product_id:
            raise UserError(_("Please select a lens product before assigning."))
        self.action_reserve_stock()
        self.message_post(
            body=_("Lens assigned and stock deducted: %s") % self.lens_product_id.name,
            message_type="notification",
        )

    def action_view_prescription(self):
        self.ensure_one()
        return {
            "name": _("Prescription"),
            "type": "ir.actions.act_window",
            "res_model": "eyekei.prescription",
            "res_id": self.prescription_id.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_view_visit(self):
        self.ensure_one()
        return {
            "name": _("Patient Visit"),
            "type": "ir.actions.act_window",
            "res_model": "eyekei.patient.visit",
            "res_id": self.visit_id.id,
            "view_mode": "form",
            "target": "current",
        }


class StockMove(models.Model):
    _inherit = "stock.move"

    # Link back to lab job for traceability
    lab_job_id = fields.Many2one("eyekei.lab.job", "Lab Job")
    is_optical_consumption = fields.Boolean(
        "Optical Lab Consumption",
        compute="_compute_is_optical",
        store=True,
    )

    def _compute_is_optical(self):
        for move in self:
            move.is_optical_consumption = bool(move.lab_job_id)
