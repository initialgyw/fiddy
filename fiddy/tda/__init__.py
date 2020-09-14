from fiddy.logger import logger
from fiddy.tda.auth import TdaAuth
from fiddy.helper import FiddyHelper
from pathlib import Path
from pytz import timezone
from typing import Union, List
import datetime as dt
import requests

tz = timezone('US/Eastern')


class Tda:
    ''' TDAmeritrade API wrapper
    
    Methods
    -------
    get_profile(symbol, cache)
    get_quote(symbols, cache)
    '''
    def __init__(self,
                 username: str = None,
                 password: str = None,
                 consumer_key: str = None,
                 redirect_uri: str = None,
                 credentials_file: str = f"{Path.home()}/.fiddy.ini",
                 data_dir: str = f"{Path.home()}/fiddy/tda",
                 base_url: str = 'https://api.tdameritrade.com',
                 verbose: int = 3):
        ''' Initialize the Tda class '''

        self.log = logger(name='TDA', verbose=verbose)
        self.auth = TdaAuth(username=username,
                            password=password,
                            consumer_key=consumer_key,
                            redirect_uri=redirect_uri,
                            credentials_file=credentials_file,
                            verbose=verbose)
        self.data_dir = data_dir
        self.base_url = base_url
        self.log.debug('TDA Initialized')

    def get_profile(self, symbol, cache: bool = True):
        ''' Get profile for a ticker '''

        symbol = symbol.upper()
        file_ = f"{self.data_dir}/{symbol}/profile.json"

        if cache:
            data = FiddyHelper.load_data(file_=file_, data_type='dict')
            if (data
                    and 'expiration' in data
                    and (dt.datetime.strptime(data['expiration'],
                                              '%Y-%m-%d').date()
                         > dt.datetime.now(tz).date())):
                self.log.debug(f"Read {symbol} profile from cache in {file_}")
                return data['profile']

        # build request
        url = f"{self.base_url}/v1/instruments"
        headers = {'Authorization': self.auth.get_access_token()}
        payload = {'symbol': symbol,
                   'projection': 'fundamental'}

        r = requests.get(url, headers=headers, params=payload)
        _, msg = FiddyHelper.check_requests(r, error_out=True)
        self.log.debug(msg)

        if not r.json():
            self.log.warning(f"{symbol} returned nothing")
            return None

        # need to modify some data
        profile = r.json()[symbol]
        profile['fundamental']['marketCap'] *= 1000000
        profile['fundamental']['marketCapFloat'] *= 1000000

        # save data
        data = {
            'expiration': str((dt.datetime.now(tz)
                              + dt.timedelta(days=1)).date()),
            'profile': profile
        }

        FiddyHelper.save_data(file_=file_, data=data, data_type='dict')
        self.log.debug(f"Saved {symbol} profile to {file_}")

        return profile

    def get_quotes(self, symbols: Union[List[str], str]):

        if isinstance(symbols, list):
            symbols = ','.join(symbols)
        symbols = symbols.upper()

        # build request
        url = f"{self.base_url}/v1/marketdata/quotes"
        headers = {'Authorization': self.auth.get_access_token()}
        payload = {'symbol': symbols}

        # get request
        r = requests.get(url, headers=headers, params=payload)
        _, msg = FiddyHelper.check_requests(r, error_out=True)
        self.log.debug(msg)

        return r.json()


if __name__ == '__main__':
    from pprint import pprint
    tda = Tda()

    # get profile
    # pprint(tda.get_profile('SNAP'))

    # get quotes
    pprint(tda.get_quotes('aapl,spy,vfiax'))
