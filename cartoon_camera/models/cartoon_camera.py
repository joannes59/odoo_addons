
#pip install onvif-zeep wsdiscovery
from odoo import models, fields, api
import os
import numpy as np
import base64
import cv2
import time
import datetime
import urllib.request
from wsdiscovery.discovery import ThreadedWSDiscovery
from onvif import ONVIFCamera
import threading
import pyudev
import codecs

class CartoonCamera(models.Model):
    _name = 'cartoon.camera'
    _description = 'Onvif Camera'

    name = fields.Char(string='Name')
    camera_type = fields.Selection([('ip', 'ip'), ('usb', 'usb')])
    device_node = fields.Char(string='Node')
    camera_model_id = fields.Many2one('cartoon.camera.model', string='Model')
    id_vendor = fields.Char(string='vendor ID', related='camera_model_id.id_vendor')

    # IP ONVIF camera
    uuid = fields.Char(string='uuid')
    ip = fields.Char(string='IP Address')
    port = fields.Integer(string='Port', default=8899)
    http = fields.Char(string='HTTP Protocol', default="http://")
    user = fields.Char(string='User', default='admin')
    password = fields.Char(string='Password', default='1234567890')
    snap_path = fields.Char(string='Snapshot Path', default="/webcapture.jpg?command=snap")
    token = fields.Char(string='Token', default="000")
    profile = fields.Text('Profile')
    ping = fields.Integer(string='Ping (ms)', default=0.0)
    wsdl_path = fields.Char(string='WDSL path', default="/addons/cartoon_camera/wsdl")

    # IP PTZ camera, movement velocity
    velocity_h = fields.Float(string='Horizontal Velocity', default=0.1)
    velocity_v = fields.Float(string='Vertical Velocity', default=0.1)

    # Composite screen camera
    nb_height = fields.Integer(string='Grid Rows', default=2)
    nb_width = fields.Integer(string='Grid Columns', default=1)




    fps = fields.Float(string='FPS', default=0.0)
    flip = fields.Boolean(string='Flip Image', default=False)


    height = fields.Integer(string='Height', default=720)
    width = fields.Integer(string='Width', default=640)


    encoded_image = fields.Binary(string="Preview", attachment=True)
    save_path = fields.Char(string='Save path', default="/home/joannes/Images/cartoon_images")

    state = fields.Selection([('draft', 'draft'), ('online', 'online'), ('enabled', 'enabled'),
                              ('error', 'error'), ('disabled', 'disabled')],
                             string='State', default='draft')

    def toggle_state(self):
        for record in self:
            if record.state not in ['disabled', 'draft']:
                record.state = 'disabled'
            elif record.state in ['disabled', 'draft', 'error', 'online']:
                record.state = 'enabled'

    def discovery_usb(self):
        """
        Discover USB cameras on the computer.
        """
        udev_context = pyudev.Context()
        devices = udev_context.list_devices(subsystem='video4linux')

        for device in devices:
            camera_ids = self.search([('device_node', '=', f'{device.device_node}'), ('camera_type', '=', 'usb')])

            if not camera_ids:
                name = f'{device.device_node}'.split('/')[-1]
                camera_vals = {
                    'name': name,
                    'device_node': f'{device.device_node}',
                    'camera_type': 'usb',
                }
                camera = camera_ids.create(camera_vals)

            elif len(camera_ids) > 1:
                camera_ids[1:].unlink()
                camera = camera_ids
            else:
                camera = camera_ids

            camera.state = 'online'
            id_vendor = device.properties.get('ID_USB_VENDOR_ID')
            id_model = device.properties.get('ID_MODEL_ID')

            if id_vendor or id_model:
                model_ids = self.env['cartoon.camera.model'].search([('id_vendor', '=', id_vendor), ('id_model', '=', id_model)])
                camera_model_id = model_ids and model_ids[0] or camera.create_camera_model_usb(device)

                if camera.camera_model_id != camera_model_id:
                    camera.camera_model_id = camera_model_id

    def create_camera_model_usb(self, device):
        """ Create the model with the device information """
        self.ensure_one()
        model_vals = {
            'id_model': device.properties.get('ID_MODEL_ID'),
            'id_vendor': device.properties.get('ID_USB_VENDOR_ID'),
            'vendor_name': codecs.decode(device.properties.get('ID_VENDOR_ENC'), 'unicode-escape'),
            'model_name': codecs.decode(device.properties.get('ID_MODEL_ENC'), 'unicode-escape'),
            }
        camera_model_id = self.env['cartoon.camera.model'].create(model_vals)
        return camera_model_id

    def discovery_ip(self):
        """
        Discover ONVIF-compatible cameras on the network.
        """
        ws_discovery = ThreadedWSDiscovery()
        ws_discovery.start()
        services = ws_discovery.searchServices()
        ws_discovery.stop()

        for service in services:
            try:
                xaddr = service.getXAddrs()[0]
                ip = xaddr.split("//")[-1].split(":")[0]
                uuid = service.getEPR().split(':')[-1]
                #service.getInstanceId())
                #service.getMessageNumber())
                #service.getMetadataVersion())
                #service.getScopes() [onvif://www.onvif.org/type/video_encoder, onvif://www.onvif.org/type/audio_encoder, onvif://www.onvif.org/hardware/IPC-model, onvif://www.onvif.org/location/country/china, onvif://www.onvif.org/name/NVT, onvif://www.onvif.org/Profile/Streaming, onvif://www.onvif.org/A1C2B3/mac/4c:60:ba:af:56:57, onvif://www.onvif.org/Profile/T]
                #service.getTypes()) [http://www.onvif.org/ver10/network/wsdl:NetworkVideoTransmitter, http://www.onvif.org/ver10/device/wsdl:Device]
                vals = {
                    'uuid': uuid,
                    'ip': ip,
                    'camera_type': 'ip',
                }
                camera_ids = self.search([('uuid', '=', uuid)])
                if camera_ids:
                    camera_ids.write(vals)
                else:
                    camera_ids.create(vals)
            except Exception as e:
                continue

    def get_wsdl_path(self):
        """ return local wsdl path """
        for camera in self:
            if not camera.wsdl_path:
                module_path = os.path.dirname(os.path.abspath(__file__))
                wsdl_path = module_path.replace('cartoon_camera/models', 'cartoon_camera/wsdl')
                camera.wsdl_path = get_wsdl_path

    def get_save_path(self, date=None, directory=None):
        # Format du nom de répertoire basé sur l'heure et la minute
        self.ensure_one()
        date = date or fields.Datetime.now()
        nom_repertoire = date.strftime("camera%Y%m%d_%H_%M")
        save_path = os.path.join(directory or self.save_path, nom_repertoire)

        # Créer le répertoire s'il n'existe pas
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        return save_path

    def get_camera_info(self):
        """ Get information on camera """
        self.get_wsdl_path()

        for camera in self:

            text_profile = ''
            # Connexion à la caméra ONVIF
            onvif_camera = ONVIFCamera(camera.ip, camera.port, camera.user, camera.password,
                                       wsdl_dir=camera.wsdl_path)
            # Service de gestion des médias
            media_service = onvif_camera.create_media_service()

            # Récupérer les profils disponibles
            profiles = media_service.GetProfiles()
            if len(profiles) >= 1:
                camera.token = profiles[0].token

            for profile in profiles:
                # URI pour les captures d'images (Snapshot URI)
                snapshot_uri = media_service.GetSnapshotUri({'ProfileToken': profile.token})
                text_profile += f"{profile.token};{profile.Name};{snapshot_uri.Uri}\n"
            camera.profile = text_profile


    def start_worker(self):
        for camera in self:
            worker_thread = threading.Thread(target=camera.continue_snapshot, daemon=True)
            worker_thread.start()

    def save_snapshot(self, directory=None):
        """ get and save snapshot """
        res = []
        for camera in self:
            time_start = time.time()
            if camera.state in ['disabled', 'draft']:
                continue

            frame = camera.get_frame()
            image = camera.save_image(frame, directory=directory)
            res.append(image)
        return res

    def get_frame_usb(self):
        """ Get a frame """
        self.ensure_one()
        camera = self
        cap = cv2.VideoCapture(camera.device_node)
        ret, frame = cap.read()
        cap.release()
        return frame

    def get_frame_ip(self):
        """ Get a frame """
        self.ensure_one()
        camera = self
        snapshot_url = f"{camera.http}{camera.ip}{camera.snap_path}"
        img = urllib.request.urlopen(snapshot_url, timeout=2)
        img_array = np.array(bytearray(img.read()), dtype=np.uint8)
        frame = cv2.imdecode(img_array, -1)
        return frame

    def get_frame(self):
        """ return frame """
        self.ensure_one()
        camera = self
        frame = None
        state = 'online'
        try:
            if camera.camera_type == 'usb':
                frame = camera.get_frame_usb()
            elif camera.camera_type == 'ip':
                frame = camera.get_frame_ip()
            else:
                state = 'error'
        except:
            state = 'error'

        if frame is None:
            frame = np.zeros((camera.height or 480, camera.width or 640, 3), dtype=np.uint8)
            state = 'error'

        if camera.flip:
            frame = cv2.flip(frame, 0)

        if camera.state != state:
            camera.state = state
        return frame

    def save_image(self, frame, directory=None):
        """ Save image """
        self.ensure_one()
        date = datetime.datetime.now()
        directory = self.get_save_path(date=date, directory=directory)
        file_name = self.name + date.strftime("_%Y%m%d_%H%M%S_") + str(date.microsecond).zfill(6) + '.png'
        file_path = os.path.join(directory, file_name)
        cv2.imwrite(file_path, frame)

        height, width, _ = frame.shape
        img_vals = {
            'name': file_name,
            'directory': directory,
            'height': height,
            'width': width,
        }
        image = self.env['cartoon.image'].create(img_vals)
        return image

    def get_snapshot(self):
        """ Get image snapshot """
        self.get_wsdl_path()

        for camera in self:
            time_start = time.time()
            frame = camera.get_frame()

            # Encoder l'image en Base64
            _, buffer = cv2.imencode('.jpg', frame)
            encoded_image = base64.b64encode(buffer).decode('utf-8')

            # Mettre à jour les champs
            height, width, _ = frame.shape
            camera.height = height
            camera.width = width
            camera.encoded_image = encoded_image
            camera.ping = int((time.time() - time_start) * 100.0)

        return True

    def pantilt(self):
        """ move the camera """
        self.get_wsdl_path()
        pan_x = self.env.context.get('pan_x', 0.0)
        pan_y = self.env.context.get('pan_y', 0.0)
        #pan_z = self.env.context.get('pan_z', 0.0)

        for camera in self:
            onvif_camera = ONVIFCamera(camera.ip, camera.port, camera.user, camera.password,
                                       wsdl_dir=camera.wsdl_path)

            ptz_service = onvif_camera.create_ptz_service()
            request = ptz_service.create_type('ContinuousMove')
            request.ProfileToken = camera.token

            # Déplacement relatif Pan-Tilt-Zoom
            if camera.flip:
                pan_y = - pan_y

            request.Velocity = {'PanTilt': {'x': pan_x * camera.velocity_v, 'y': pan_y * camera.velocity_h}}
            #                                'Zoom': {'x': pan_z}}

            # Exécution de la commande
            ptz_service.ContinuousMove(request)
            time.sleep(0.25)
            ptz_service.Stop({'ProfileToken': camera.token})
            camera.get_snapshot()
