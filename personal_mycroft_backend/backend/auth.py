# Copyright 2019 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from personal_mycroft_backend.backend import API_VERSION, DEBUG, SQL_DEVICES_URI
from personal_mycroft_backend.utils import nice_json, gen_api
from personal_mycroft_backend.backend.decorators import noindex, requires_admin
from personal_mycroft_backend.database import model_to_dict
from personal_mycroft_backend.database.devices import DeviceDatabase
from flask import request, Response
import time


def get_auth_routes(app):
    @app.route("/" + API_VERSION + "/pair/<code>/<uuid>/<name>/<mail>",
               methods=['PUT'])
    @noindex
    @requires_admin
    def pair(code, uuid, name, mail):
        # pair
        result = {"paired": False}
        with DeviceDatabase(SQL_DEVICES_URI, debug=DEBUG) as device_db:
            device = device_db.get_unpaired_by_uuid(uuid)
            if device and device.code == code:
                user = device_db.get_user_by_mail(mail)
                # create user if it doesnt exist
                if not user:
                    device_db.add_user(mail, name, "666")
                if device_db.add_device(uuid, mail=mail):
                    device_db.remove_unpaired(uuid)
                    result = {"paired": True}
        return nice_json(result)

    @app.route("/" + API_VERSION + "/auth/token", methods=['GET'])
    @noindex
    def token():
        api = request.headers.get('Authorization', '').replace("Bearer ", "")
        with DeviceDatabase(SQL_DEVICES_URI, debug=DEBUG) as device_db:
            device = device_db.get_device_by_token(api)
            if not device:
                return Response(
                    'Could not verify your access level for that URL.\n'
                    'You have to authenticate with proper credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="NOT PAIRED"'})
            # token to refresh expired token
            if device.refreshToken is None or device.refreshToken != api:
                return Response(
                    'Could not verify your access level for that URL.\n'
                    'You have to authenticate with proper credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="BAD REFRESH CODE"'})
            # new tokens to access
            access_token = gen_api()
            new_refresh_token = gen_api()

            device_db.add_device(uuid=device.uuid,
                                 expires_at=time.time() + 72000,
                                 accessToken=access_token,
                                 refreshToken=new_refresh_token)
            result = model_to_dict(device)
        return nice_json(result)

    return app
