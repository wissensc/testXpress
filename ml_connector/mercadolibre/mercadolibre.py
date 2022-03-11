
"""
MercadoLibre Integration Library
@author wissen - structure based in library MercadoPago @hcasatti
"""

import requests
import json


class MLException(Exception):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value


class InvalidCredentials(MLException):
    pass


class ML(object):
    version = "1.0.0"

    def __init__(self, *args):
        """
        Instantiate ML with credentials and get token with get_access_token():
        mp = mercadoplibre.ML(client_id, client_secret, code, redirect_uri)
        Instantiate ML with refresh token and get token with get_refresh_token():
        mp = mercadolibre.ML(client_id, client_secret, refresh_token)
        Instantiate ML with refresh token active:
        mp = mercadolibre.ML(refresh_token)

        """
        if len(args) == 4:
            self.__client_id = args[0]
            self.__client_secret = args[1]
            self.__code = args[2]
            self.__redirect_uri = args[3]
        elif len(args) == 3:
            self.__client_id = args[0]
            self.__client_secret = args[1]
            self.__refresh_token = args[2]
        elif len(args) == 1:
            self.__access_token = args[0]
        else:
            raise InvalidCredentials(None)
        self.__rest_client = self.__RestClient(self)

    def get_access_token(self):
        app_client_values = {
            "grant_type": "authorization_code",
            "client_id": self.__client_id,
            "client_secret": self.__client_secret,
            "code": self.__code,
            "redirect_uri": self.__redirect_uri
        }
        access_data = self.__rest_client.post("/oauth/token", app_client_values)
        return access_data

    def get_refresh_token(self):
        app_client_values = {
            "grant_type": "refresh_token",
            "client_id": self.__client_id,
            "client_secret": self.__client_secret,
            "refresh_token": self.__refresh_token,
        }
        access_data = self.__rest_client.post("/oauth/token", app_client_values)
        return access_data

    def get(self, uri):
        return self.__rest_client.get(uri, {}, self.__access_token)

    def put(self, uri, data):
        return self.__rest_client.put(uri, data, self.__access_token)

    def get_notification_details(self, uri, topic):
        resource = uri
        if topic == 'messages':
            resource = "/messages/{}".format(resource)
        return self.__rest_client.get(resource, {}, self.__access_token)

    def get_user(self, user_id):
        return self.__rest_client.get("/users/{}".format(user_id), {}, self.__access_token)

    def get_items_seller(self, site_id, user_id):
        return self.__rest_client.get("/sites/{}/search?seller_id={}".format(site_id, user_id), {}, self.__access_token)

    def get_product(self, item_id):
        return self.__rest_client.get("/items/{}".format(item_id), {}, self.__access_token)

    def get_inventory_full(self, inventory_id):
        return self.__rest_client.get("/inventories/{}/stock/fulfillment".format(inventory_id), {}, self.__access_token)

    def update_stock(self, item_id, quantity):
        data = {
        "available_quantity": quantity
        }
        return self.__rest_client.put("/items/{}".format(item_id), data, self.__access_token)

    def update_variation(self, item_id, variation_id, quantity):
        data = {
                "variations": [{
                    "id": variation_id,
                    "available_quantity": quantity
                }]
            }
        return self.__rest_client.put("/items/{}".format(item_id), data, self.__access_token)

    def send_message(self, text, pack_id, seller_id, buyer_id):
        data = {
            "from": {
                "user_id": seller_id
            },
            "to": {
                "user_id": buyer_id
            },
            "text": text
        }
        return self.__rest_client.post("/messages/packs/{}/sellers/{}?tag=post_sale".format(pack_id, seller_id), data, self.__rest_client.MIME_JSON, self.__access_token)

    class __RestClient(object):
        __API_BASE_URL = "https://api.mercadolibre.com"
        MIME_JSON = "application/json"
        MIME_FORM = "application/x-www-form-urlencoded"

        def __init__(self, outer):
            self.__outer = outer
            self.USER_AGENT = "MercadoLibre Python conector v" + self.__outer.version

        def get(self, uri, data=None, access_token=None):
            api_result = requests.get("{}{}".format(self.__API_BASE_URL, uri), data=data, headers={'User-Agent': self.USER_AGENT, "Authorization": "Bearer %s" % access_token})
            response = {
                "status": api_result.status_code,
                "response": api_result.json()
            }

            return response

        def post(self, uri, data=None, content_type=MIME_FORM, access_token=None):
            headers = {
                'User-Agent': self.USER_AGENT,
                'Content-type': content_type,
                'Accept': self.MIME_JSON,
            }
            if data is not None:
                data = json.dumps(data)
            if content_type == self.MIME_JSON:
                del headers['Accept']
                headers['Authorization'] = "Bearer %s" % access_token

            api_result = requests.post("{}{}".format(self.__API_BASE_URL, uri), data=data, headers=headers)
            response = {
                "status": api_result.status_code,
                "response": api_result.json()
            }

            return response

        def put(self, uri, data=None, access_token=None):
            headers = {
                    'User-Agent': self.USER_AGENT,
                    'Content-type': self.MIME_JSON
            }
            data = json.dumps(data)
            headers['Authorization'] = "Bearer %s" % access_token

            api_result = requests.put("{}{}".format(self.__API_BASE_URL, uri), data=data, headers=headers)

            response = {
                "status": api_result.status_code,
                "response": api_result.json()
            }

            return response

        def delete(self, uri, data=None, access_token=None):
            api_result = requests.get("{}{}".format(self.__API_BASE_URL, uri), data=data, headers={'User-Agent': self.USER_AGENT, "Authorization": "Bearer %s" % access_token})

            response = {
                "status": api_result.status_code,
                "response": api_result.json()
            }

            return response
