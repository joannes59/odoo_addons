from odoo import models, fields, api
import fsspec
import logging
_logger = logging.getLogger(__name__)


class CartoonStorage(models.Model):
    _name = "cartoon.storage"
    _description = "Storage"

    parent_id = fields.Many2one('cartoon.storage', string='Parent Storage')
    name = fields.Char(string='Name', required=True)
    path = fields.Char(string='Path', required=True)
    protocol = fields.Selection(
        selection="_get_protocols",
        required=True,
        help="The protocol used to access the content of filesystem.\n"
        "This list is the one supported by the fsspec library (see "
        "https://filesystem-spec.readthedocs.io/en/latest). A filesystem protocol"
        "is added by default and refers to the odoo local filesystem.\n"
        "Pay attention that according to the protocol, some options must be"
        "provided through the options field.",
    )
    options = fields.Text(string='Options')
    creation_date = fields.Datetime(string='Creation Date')
    update_date = fields.Datetime(string='Update Date')
    state = fields.Char(string='State')
    host = fields.Char(string='Host')
    port = fields.Integer(string='Port')
    username = fields.Char(string='Username')
    password = fields.Char(string='Password')

    @api.model
    def _get_protocols(self) -> list[tuple[str, str]]:
        protocol = []
        for p in fsspec.available_protocols():
            try:
                cls = fsspec.get_filesystem_class(p)
                protocol.append((p, f"{p} ({cls.__name__})"))
            except ImportError as e:
                _logger.debug("Cannot load the protocol %s. Reason: %s", p, e)
        return protocol

    def check_path(self):
        """
        check the directory_path
        :return:
        """
        for storage in self:
            directory_path = storage.protocol + '://' + storage.path
            fs = fsspec.filesystem(storage.protocol)

            # Vérifier si le chemin est un répertoire valide
            if not fs.exists(directory_path):
                raise FileNotFoundError(f"The path '{directory_path}' don't exist.")
            storage.state == 'ok'
        return True

    def list_path(self):
        """
        Liste tous les répertoires et fichiers.
        """
        for storage in self:
            storage.check_path()
            fs = fsspec.filesystem(storage.protocol)
            info = fs.info(storage.path)
            condition = [('path', '=', storage.path), ('storage_id', '=', storage.id)]
            path_ids = self.env['cartoon.path'].search(condition)
            vals = self.env['cartoon.path'].prepare_vals(storage, info)

            if len(path_ids) == 1:
                path_ids.update(vals)
                path_ids.update_extension()
            elif not path_ids:
                path_ids.create(vals)
                path_ids.update_extension()
            else:
                path_ids.state = 'error'





