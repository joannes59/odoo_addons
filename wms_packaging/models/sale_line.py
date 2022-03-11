# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import get_lang


import logging
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    packaging_qty = fields.Float("Pack Qty", default=1.0)

    def _prepare_invoice_line(self, **optional_values):
        inv_line_values = super(SaleOrderLine, self)._prepare_invoice_line( **optional_values)

        if self.product_packaging.qty:
            inv_line_values['product_packaging'] = self.product_packaging.id
            inv_line_values['packaging_qty'] = inv_line_values['quantity'] / self.product_packaging.qty
        else:
            inv_line_values['product_packaging'] = False
            inv_line_values['packaging_qty'] = inv_line_values['quantity']
        return inv_line_values

    @api.onchange('packaging_qty')
    def onchange_packaging_qty(self):
        "change qty if package is set"
        if self.product_packaging:
            self.product_uom_qty = self.packaging_qty * self.product_packaging.qty
        else:
            self.product_uom_qty = self.packaging_qty

    @api.onchange('product_packaging')
    def _onchange_product_packaging(self):
        if self.product_packaging:
            self.packaging_qty = 1.0
        self.onchange_packaging_qty()

    @api.onchange('product_id')
    def product_id_change(self):
        "add packaging"
        if not self.product_id:
            return
        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
        vals['product_uom_qty'] = 1.0
        vals['product_packaging'] = False
        vals['packaging_qty'] = 1.0

        if self.product_id.sale_unit:
            for line in self.product_id.packaging_ids:
                if line.sale_unit == self.product_id.sale_unit:
                    vals['product_packaging'] = line.id
                    vals['product_uom_qty'] = self.product_packaging.qty
                    break

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        vals.update(name=self.get_sale_order_line_multiline_description_sale(product))

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
        self.update(vals)

        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s", product.name)
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False

        return result
