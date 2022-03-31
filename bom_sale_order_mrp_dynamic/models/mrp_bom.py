
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
import unicodedata

import logging
_logger = logging.getLogger(__name__)


def remove_accents(input_str):
    only_ascii = unicodedata.normalize('NFD', input_str).encode('ascii', 'ignore')
    if type(only_ascii) == bytes:
        return only_ascii.decode()
    else:
        return only_ascii


def txt_cleanup(text):
    """Return a compatible text with python variable notation"""
    if text:
        text = remove_accents(text)
        text = text.strip()
        for char in '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~\n':
            text = text.replace(char, ' ')
        for char in [('    ', ' '), ('   ', ' '), ('  ', ' '), (' ', '_')]:
            text = text.replace(char[0], char[1])
        return text
    else:
        return ''


def convert_to_float(text):
    "convert to float"
    out_str = ""
    if text:
        for char in text:
            # TODO: Use Country decimal notation function
            if char.isnumeric() or char in [',', '.']:
                out_str += char
        out_str = out_str.replace(',', '.')
        try:
            res = float(out_str or 0.0)
        except:
            res = 0.0
    else:
        res = 0.0
    return res


class MrpBomParameter(models.Model):
    _name = "mrp.bom.parameter"
    _description = "Parameter value for computing and search"

    bom_id = fields.Many2one('mrp.bom', 'Bill of materials')
    attribute_id = fields.Many2one('product.attribute', 'Attribute')
    name = fields.Char('name', related='attribute_id.code', store=True)
    value = fields.Char('Value')

    @api.onchange('value')
    def onchange_value(self):
        """on change convert to float if needed"""
        if self.attribute_id.convert_type == 'float':
            self.value = convert_to_float(self.value)


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    parameter_ids = fields.One2many('mrp.bom.parameter', 'bom_id', string='Parameters')
    sale_line_id = fields.Many2one('sale.order.line', "Sale line")
    sale_id = fields.Many2one('sale.order', 'Sale order', related='sale_line_id.order_id')

    def compute_line(self, data={}):
        """Compute the line"""
        for bom in self:
            for line in bom.bom_line_ids:
                line.compute_line(data=data)
            for line in bom.operation_ids:
                line.compute_line(data=data)

    def get_attribute_value(self):
        """Get attribute value with conversion to float or text"""
        self.ensure_one()
        res = {}
        for line in self.parameter_ids:
            if line.attribute_id and line.attribute_id.convert_type == 'float':
                value = convert_to_float(line.value)
            else:
                value = line.value
            res.update({line.name: value})
        return res

    def delete_attribute(self):
        """delete previous attribute parameters"""
        for bom in self:
            for line in bom.parameter_ids:
                if line.attribute_id:
                    line.unlink()

    def update_custom_value(self):
        """ Get custom value"""
        self.ensure_one()
        res = {}
        for custom in self.sale_line_id.product_custom_attribute_value_ids:
            custom_attribute = custom.custom_product_template_attribute_value_id.attribute_id
            custom_value = custom.custom_value
            res.update({str(custom_attribute.id): custom_value})
        for line in self.parameter_ids:
            if str(line.attribute_id.id) in list(res.keys()):
                line.value = res[str(line.attribute_id.id)]
                line.onchange_value()
        return res

    def create_attribute_value(self):
        """Get attribute value with conversion to float or text"""
        for bom in self:
            if bom.product_id:
                attribute_value_ids = bom.product_id.product_template_attribute_value_ids
            elif bom.product_tmpl_id:
                attribute_value_ids = bom.product_tmpl_id.attribute_line_ids
            else:
                bom.delete_attribute()

            for line in attribute_value_ids:
                attribute_id = line.attribute_id.id
                condition = [('bom_id', '=', bom.id), ('attribute_id', '=', attribute_id)]
                parameter_ids = self.env['mrp.bom.parameter'].search(condition)

                if not parameter_ids:
                    parameters_vals = {
                        'bom_id': bom.id,
                        'attribute_id': attribute_id,
                    }
                    if bom.product_id:
                        parameters_vals['value'] = line.name
                    parameter = self.env['mrp.bom.parameter'].create(parameters_vals)
                    if not parameter.name:
                        parameter.name = txt_cleanup(line.attribute_id.name)
                else:
                    parameter = parameter_ids[0]
                    if bom.product_id:
                        parameter.value = line.name
                parameter.onchange_value()

            bom.update_custom_value()


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    python_compute = fields.Text(string='Computing', default="",
                                 help="Compute the new quantity or product by formula.\n\n"
                                      ":param line: actual BOM line\n"
                                      ":param attribute: name of attribute value\n\n"
                                      "Return value by create variable:\n"
                                      "product_qty = float\n"
                                      "product_id = product.product recordset singleton\n")

    def compute_line(self, data={}):
        """ Compute the python code on template to complete the product value"""
        return self.env['product.template'].compute_python_code(self)





