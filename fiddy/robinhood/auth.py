from fiddy.logger import logger
from fiddy.helper import FiddyHelper
from pathlib import Path
from pytz import timezone
import datetime as dt

tz = timezone('US/Eastern')


class RHAuth:
    ''' Robinhood Authentication class

    Attributes
    ----------

    Methods
    -------
    '''

    def __init__(self,
                 username: str = None,
                 password: str = None,
                 two_fa_secret: str = None,
                 credentials_file: str = f"{Path.home()}/.fiddy.ini",
                 cache: bool = True,
                 save: bool = True,
                 verbose: int = 3) -> None:
        ''' Initialize the RHAuth class '''
        self.log = logger(name='RHAuth', verbose=verbose)
        self.credentials_file = credentials_file
        self.cache = cache
        self.save = save

        # initialize credentials variable
        self.credentials = {
            'username': username,
            'password': password,
            'two_fa_secret': two_fa_secret,
            'access_token': None,
            'expires_in': None
        }

        # load from credentials file
        if self.cache:
            self.log.debug('Cache is set to True. '
                           f"Loading credentials from {self.credentials_file}")
            credentials = FiddyHelper.load_credentials(self.credentials_file)
        else:
            self.log.debug('Not loading from cache')
            credentials = {}

        # update the self.credentials
        for key in self.credentials.keys():
            try:
                if not self.credentials[key] and credentials['Robinhood'][key]:
                    self.credentials[key] = credentials['Robinhood'][key]
            except KeyError:
                self.log.debug(f"Will need to get {key}")

        self.prompt_credentials()

    def prompt_credentials(self) -> None:
        ''' Prompt for credentials '''
        for key in ['username', 'password', 'two_fa_secret']:
            if key == 'password' and not self.credentials[key]:
                from getpass import getpass
                self.credentials[key] = getpass(prompt=f"Robinhood {key}: ")
            elif not self.credentials[key]:
                self.credentials[key] = input(f"Robinhood {key}: ")

    def get_device_token(self) -> None:
        ''' Get Robinhood requires unique device_id '''
        import random

        rands = []
        for i in range(0, 16):
            r = random.random()
            rand = 4294967296.0 * r
            rands.append((int(rand) >> ((3 & i) << 3)) & 255)

        hexa = []
        for i in range(0, 256):
            hexa.append(str(hex(i+256)).lstrip("0x").rstrip("L")[1:])

        id = ''
        for i in range(0, 16):
            id += hexa[rands[i]]
            if (i == 3) or (i == 5) or (i == 7) or (i == 9):
                id += "-"

        return id

    def get_mfa_token(self):
        ''' Get the unique timed token '''
        import base64
        import hmac
        import time
        import struct
        import hashlib

        intervals_no = int(time.time())//30
        key = base64.b32decode(self.credentials['two_fa_secret'], True)
        msg = struct.pack(">Q", intervals_no)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        o = h[19] & 15
        h = '{0:06d}'.format(
            (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000)

        return h

    def request_access_token(
            self,
            url='https://api.robinhood.com/oauth2/token/') -> str:
        ''' Request access token '''
        import requests

        payload = {
          'client_id': 'c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS',
          'grant_type': 'password',
          'password': self.credentials['password'],
          'username': self.credentials['username'],
          'scope': 'internal',
          'mfa_code': self.get_mfa_token(),
          'device_token': self.get_device_token()
        }

        # request token
        r = requests.post(url, data=payload)
        _, msg = FiddyHelper.check_requests(r, error_out=True)
        self.log.debug(msg)

        self.credentials['access_token'] = r.json()['access_token']
        self.credentials['expires_in'] = \
            str((dt.datetime.now(tz)
                 + dt.timedelta(seconds=r.json()['expires_in'])))

    def get_access_token(self):
        ''' Get access token '''

        # validate token in cache
        if self.cache and (self.credentials['access_token']
                           and self.credentials['expires_in']):
            if (dt.datetime.now(tz)
                < dt.datetime.strptime(self.credentials['expires_in'],
                                       '%Y-%m-%d %H:%M:%S.%f%z')):
                self.log.debug(f"Token in {self.credentials_file} "
                               'is still valid')
                return self.credentials['access_token']

        # get new token
        self.request_access_token()

        # save
        if self.save:
            FiddyHelper.save_credentials(file_=self.credentials_file,
                                         section='Robinhood',
                                         credentials=self.credentials)

        return self.credentials['access_token']


if __name__ == '__main__':
    print(RHAuth().get_access_token())
