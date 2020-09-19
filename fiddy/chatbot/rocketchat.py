from fiddy.logger import logger
from fiddy.helper import FiddyHelper
from fiddy.chatbot.get_ticker_info import rocketchatbot
from pathlib import Path
import websocket
import json
import random
import hashlib
import requests
import re
import multiprocessing
from pprint import pprint


class RocketChatBot:
    ''' Real time quote for rocket chat bot '''
    def __init__(self,
                 credentials_file: str = f"{Path.home()}/.fiddy.ini",
                 section: str = 'APN RocketChat',
                 channels: str = None,
                 verbose: int = 3) -> None:

        self.log = logger('RocketChatBot', verbose=verbose)

        # load the credentials
        try:
            credentials = FiddyHelper.load_credentials(
                            credentials_file)[section]
        except KeyError:
            self.log.error(f"Section {section} is not in {credentials_file}")
            exit(1)

        # validate credentials
        for required_key in ['username', 'password', 'url']:
            if required_key not in credentials.keys():
                raise KeyError(f"{required_key} is not found in "
                               f"{section} section of {credentials_file}")

        self.credentials = credentials

        # set websocket verbosity
        if verbose == 3:
            websocket.enableTrace(True)

        # get headers for REST API
        self.rest_login()

        # get channel_ids
        if channels is None:
            raise ValueError('Channels for subscription is required.')
        else:
            channels = channels.split(',')

        self.get_channel_ids(channels)

    def rest_login(self) -> None:
        ''' Get credentials for user_id and auth_token

        Attributes
        ----------
        request_header
        '''
        url = f"https://{self.credentials['url']}/api/v1/login"
        payload = {
            'user': self.credentials['username'],
            'password': self.credentials['password']
        }

        r = requests.post(url, data=payload)
        _, msg = FiddyHelper.check_requests(r, error_out=True)
        self.log.debug(msg)

        self.request_header = {
            'X-Auth-Token': r.json()['data']['authToken'],
            'X-User-Id': r.json()['data']['userId']
        }

    def get_channel_ids(self, channels) -> None:
        ''' Get channel IDs

        Attributes
        ----------
        channels
        '''
        # get all the rooms
        url = f"https://{self.credentials['url']}/api/v1/channels.list"

        r = requests.get(url, headers=self.request_header)

        self.channel_ids: list = []
        for channel in channels:
            id_ = [c['_id'] for c in r.json()['channels']
                   if c['name'] == channel][0]
            self.channel_ids.append(id_)

        self.log.debug(f"VAR: channel_ids = {self.channel_ids}")

    def start_connection(self):
        connect_data = {
            'msg': 'connect',
            'version': '1',
            'support': ['1']
        }
        self.log.debug('Initating connection')
        self.ws.send(json.dumps(connect_data))

    def send_login(self):
        ''' Send login credentials to server
        RocketChat requires password to be in SHA256
        '''
        connection_num = str(random.randint(1, 1000))
        password = bytes(self.credentials['password'], 'utf-8')

        login_data = {
            'msg': 'method',
            'method': 'login',
            'id': connection_num,
            'params': [{
                'user': {'username': self.credentials['username']},
                'password': {'digest': hashlib.sha256(password).hexdigest(),
                             'algorithm': 'sha-256'}
            }]
        }
        self.ws.send(json.dumps(login_data))
        self.log.debug('Sent login. '
                       f"Connection # {connection_num}")

    def subscribe_to_channel(self):
        for channel_id in self.channel_ids:
            subscription_data = {
                'msg': 'sub',
                'id': str(random.randint(1, 1000)),
                'name': 'stream-room-messages',
                'params': [
                    channel_id, False
                ]
            }

            self.ws.send(json.dumps(subscription_data))
            self.log.debug(f"Subscribed to {channel_id}")

    def on_open(self):
        self.start_connection()
        self.send_login()
        self.subscribe_to_channel()

    def on_ping(self):
        self.log.debug('Pong back')
        self.ws.send(json.dumps({'msg': 'pong'}))

    def on_message(self, message):
        message = json.loads(message)
        self.log.debug(message)
        pprint(message)

        if 'msg' in message and message['msg'] == 'ping':
            self.on_ping()
        elif ('msg' in message
              and 'collection' in message
              and message['collection'] == 'stream-room-messages'):
            msg = message['fields']['args'][0]['msg']

            # get tickers from the msg
            tickers = [word for word in msg.split(' ')
                       if re.match(r'^\$\D+', word)]
            tickers = list(set(tickers))
            tickers = [ticker.strip(r'\$') for ticker in tickers]

            if tickers:
                for ticker in tickers:
                    self.log.debug("Processing {ticker}")
                    multiprocessing.Process(target=rocketchatbot,
                                            args=(ticker,
                                                  self.credentials['url'],
                                                  self.channel_ids[1],
                                                  self.request_header)).start()

    def ws_connect(self):
        url = f"wss://{self.credentials['url']}/websocket"
        self.log.debug(f"VAR: url = {url}")
        self.ws = websocket.WebSocketApp(url,
                                         on_open=self.on_open,
                                         on_message=self.on_message)
        self.ws.run_forever()


if __name__ == '__main__':
    RocketChatBot(channels='gwang-test,finance').ws_connect()
