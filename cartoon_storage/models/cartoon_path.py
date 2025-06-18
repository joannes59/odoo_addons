from odoo import models, fields, api
from datetime import datetime
import fsspec

class CartoonPath(models.Model):
    _name = "cartoon.path"
    _description = "Path to directory and file"

    parent_id = fields.Many2one('cartoon.path', string='Parent path', index=True)
    child_ids = fields.One2many('cartoon.path', 'parent_id', string='Subpaths')
    storage_id = fields.Many2one('cartoon.storage', string='Storage', index=True)
    name = fields.Char(string='Name', required=True, index=True)
    path = fields.Char(string='Path', required=True, index=True)
    size = fields.Float(string='Size')
    file_count = fields.Integer(string='File Count')
    mounted_storage_id = fields.Many2one('cartoon.storage', string='Mounted Storage', index=True)
    creation_date = fields.Datetime(string='Creation Date')
    update_date = fields.Datetime(string='Update Date')
    ino = fields.Integer(string='Inode', index=True)
    islink = fields.Boolean('Is link')
    isfile = fields.Boolean('Is file')
    path_type = fields.Char(string='Type', required=True, index=True)
    extension_id = fields.Many2one('cartoon.path.extension', string='Extension', index=True)
    state = fields.Char(string='State')

    @api.model
    def prepare_vals(self, storage, info, parent_id=None):
        """ return vals with data come from fs info
        info exemple: {'name': '/home/user/Images/administratif', 'size': 4096, 'type': 'directory', 'created': 1734898657.0559402, 'islink': False, 'mode': 16877, 'uid': 1000, 'gid': 1000, 'mtime': 1734898657.0559402, 'ino': 3670030, 'nlink': 2}
        """
        vals = {
            'storage_id': storage.id,
            'path': info.get('name'),
            'parent_id': parent_id or False,
            'name': info.get('name').split('/')[-1],
            'ino': info.get('ino'),
            'creation_date': datetime.fromtimestamp(info.get('created')),
            'update_date': datetime.fromtimestamp(info.get('mtime')),
            'islink': info.get('islink'),
            'path_type': info.get('type'),
            'state': 'ok',
            }
        if info.get('type') == 'file':
            vals.update({'isfile': True, 'size': info.get('size')})

        return vals

    def update_extension(self):
        """ define extension """
        extension_map = {}
        for path in self:
            if path.isfile and path.name and '.' in path.name and path.name[0] != '.':
                extension_name = path.name.split('.')[-1]
                if extension_name.isnumeric():
                    continue
                if extension_name != path.extension_id.name:
                    if extension_name not in list(extension_map.keys()):
                        extension_ids = self.env['cartoon.path.extension'].search([('name', '=', extension_name)], limit=1)
                        if not extension_ids:
                            extension_ids = self.env['cartoon.path.extension'].create({'name': extension_name})
                        extension_map[extension_name] = extension_ids.id
                    path.update({'extension_id': extension_map[extension_name]})

    def update_info(self, recursive=False):
        """ update path """
        recursive = recursive or self.env.context.get('recursive') or False
        storage_fs = {}
        for path in self:
            if path.storage_id not in list(storage_fs.keys()):
                # Save filesystem in storage_fs
                storage_fs[path.storage_id] = fsspec.filesystem(path.storage_id.protocol)
            fs = storage_fs[path.storage_id]

            previews_subpath_s = path.child_ids
            new_subpath_s = self.env['cartoon.path']
            all_subpath_s = self.env['cartoon.path']

            for info_subpath in fs.ls(path.path, detail=True):
                if info_subpath.get('ino'):
                    condition = [('ino', '=', info_subpath.get('ino')), ('storage_id', '=', path.storage_id.id)]
                elif info_subpath.get('name'):
                    condition = [('path', '=', info_subpath.get('name')), ('storage_id', '=', path.storage_id.id)]
                else:
                    continue

                subpath_ids = self.env['cartoon.path'].search(condition)
                vals = self.prepare_vals(path.storage_id, info_subpath, parent_id=path.id)
                if not subpath_ids:
                    new_subpath_s |= subpath_ids.create(vals)
                elif len(subpath_ids) == 1:
                    subpath_ids.update(vals)
                    all_subpath_s |= subpath_ids
                else:
                    subpath_ids.state = 'error'
                    all_subpath_s |= subpath_ids

                (previews_subpath_s - all_subpath_s).state = 'deleted'
                (new_subpath_s + all_subpath_s).update_extension()

            if recursive:
                for subfolder in path.child_ids:
                    if subfolder.path_type in ['directory']:
                        subfolder.update_info(recursive=True)











