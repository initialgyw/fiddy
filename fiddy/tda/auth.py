from fiddy.logger import logger
from fiddy.helper import FiddyHelper
from pathlib import Path
from splinter import Browser
from pytz import timezone
import datetime as dt
import requests
import time
import urllib

tz = timezone('US/Eastern')


class TdaAuth:
    ''' TDAmeritrade Authentication

    Attributes
    ----------

    Methods
    -------

    '''
    def __init__(self,
                 credentials_file: str = f"{Path.home()}/.fiddy.ini",
                 username: str = None,
                 password: str = None,
                 consumer_key: str = None,
                 redirect_uri: str = None,
                 verbose: int = 3) -> None:
        ''' Initialize TdaAuth class

        Parameters
        ----------
        credentials_file : str
            read and/or store credentials, required
        username: str
            TD Ameritrade username, overrides credentials_file
        password: str
            TD Ameritrade password, overrides credentials_file
        consumer_key: str
            TD Ameritrade Developer app key, overrides credentials_file
        redirect_uri: str
            TD Ameritrade Developer app redirect, overrides credentials_file
        '''

        self.log = logger(name='TdaAuth', verbose=verbose)
        self.credentials_file = credentials_file
        self.credentials = {
            'username': username,
            'password': password,
            'consumer_key': consumer_key,
            'redirect_uri': redirect_uri,
            'code': None,
            'access_token': None,
            'access_token_expiration': None,
            'refresh_token': None,
            'refresh_token_expiration': None,
            'token_type': None
        }

        # read credentials from file
        credentials = FiddyHelper.load_credentials(self.credentials_file)
        # Set the credentials from file
        for key in self.credentials.keys():
            try:
                if (not self.credentials[key]
                        and credentials['TdaAmeritrade'][key]):
                    self.credentials[key] = credentials['TdaAmeritrade'][key]
            except KeyError:
                self.log.warning(f"{key} is not provide nor is it set")

        self.prompt_credentials()

    def prompt_credentials(self) -> None:
        ''' Prompt for necessary credentials if not provided '''

        required_keys = ['username',
                         'password',
                         'consumer_key',
                         'redirect_uri']

        for key in required_keys:
            prompt = f"TDA Ameritrade {key}: "
            if key == 'password' and not self.credentials['password']:
                from getpass import getpass
                self.credentials['password'] = getpass(prompt=prompt)
                continue

            if not self.credentials[key]:
                self.credentials[key] = input(prompt)

    def get_code(self,
                 url: str = 'https://auth.tdameritrade.com/auth?',
                 webdriver: str = '/usr/local/bin/chromedriver',
                 browser_type: str = 'chrome') -> str:
        ''' Get TDAmeritrade request token

        Parameters
        ----------
        webdriver: str, defaults to /usr/local/bin/chromedriver
            webdriver for automation
        browser_type: str, defaults to chrome
            the web browser to use
        url: str, defaults to https://auth.tdameritrade.com/auth?
            url to OAuth

        Returns
        -------
        code
        '''

        assert Path(webdriver).is_file(), \
            'Unable to locate {}'.format(webdriver)

        # path to locate the webdriver
        executable_path = {'executable_path': webdriver}

        # Create the instance of the browser
        browser = Browser(browser_type, **executable_path, headless=False)

        # Build the URL and payload for browser
        payload = {'response_type': 'code',
                   'redirect_uri': self.credentials['redirect_uri'],
                   'client_id': (self.credentials['consumer_key']
                                 + '@AMER.OAUTHAP')}

        # build the URL and store it in a new variable
        oauth_url = requests.Request('GET', url, params=payload).prepare().url

        # open the browser for the url
        browser.visit(oauth_url)

        # fill out each part of the form and click submit
        browser.find_by_id("username0").first.fill(
            self.credentials['username'])
        browser.find_by_id("password").first.fill(
            self.credentials['password'])

        # click the log in button
        browser.find_by_id("accept").first.click()
        time.sleep(1)

        # click continue on Get Code Via Text Message
        browser.find_by_id("accept").first.click()

        # Enter 2fa code, Click trust this device. DO NOT CLICK CONTINUE
        time.sleep(30)
        browser.find_by_id("accept").first.click()

        # Accept TD Ameritrade Authorization
        browser.find_by_id("accept").first.click()

        # give it a second, then grab the url
        time.sleep(1)
        code_url = browser.url

        # grab the part we need, and decode it.
        self.credentials['code'] = \
            urllib.parse.unquote(code_url.split('code=')[1])

        # close the browser
        browser.quit()

    def get_access_token(
            self,
            url: str = 'https://api.tdameritrade.com/v1/oauth2/token',
            save: bool = True,
            cache: bool = True) -> str:
        ''' Get access token for TD Ameritrade

        Parameters
        ----------
        url : str
            URL to get access token
            defaults = https://api.tdameritrade.com/v1/oauth2/token
        cache : bool
            if False, will immediately get new code, refresh and access token
            default = True

        Returns
        -------
        access_token: str
            30 minute access token from POST
        '''
        # get the time now to validate access token
        time_now = dt.datetime.now(tz)

        # define url headers and payload
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {
            'grant_type': 'authorization_code',
            'access_type': 'offline',
            'client_id': self.credentials['consumer_key'],
            'redirect_uri': self.credentials['redirect_uri'],
        }
        # get code if code is not provided
        if not self.credentials['code']:
            self.get_code()
        payload['code'] = self.credentials['code']

        required_credential_keys = [
            'code',
            'access_token',
            'access_token_expiration',
            'refresh_token',
            'refresh_token_expiration',
            'token_type'
        ]
        # check to see if all the necessary keys are in credentials file
        if cache and all([self.credentials[key]
                          for key in required_credential_keys]):
            refresh_token_expiration = dt.datetime.strptime(
                self.credentials['refresh_token_expiration'],
                '%Y-%m-%d %H:%M:%S %Z%z')
            access_token_expiration = dt.datetime.strptime(
                self.credentials['access_token_expiration'],
                '%Y-%m-%d %H:%M:%S %Z%z')

            # check to see if all the token keys are valid
            if (refresh_token_expiration > time_now and
                    access_token_expiration > time_now):
                self.log.debug('Refresh token and access token '
                               f"are still valid from {self.credentials_file}")
                return '{} {}'.format(self.credentials['token_type'],
                                      self.credentials['access_token'])

            elif (refresh_token_expiration > time_now and
                    access_token_expiration < time_now):
                self.log.debug('Access token expired. Acquiring new one.')
                # set the payload to request a new access_token
                payload['grant_type'] = 'refresh_token'
                payload['refresh_token'] = self.credentials['refresh_token']

        try:
            # post the data to get the token
            r = requests.post(url, headers=headers, data=payload)
        except Exception as err:
            self.log.error(err)
            raise

        # Get expiration dates of request and access tokens
        # 5 minutes less
        access_token_expiration = (
            time_now
            + dt.timedelta(seconds=r.json()['expires_in'] - 300))
        self.log.debug('Set access_token_expiration to '
                       f"{access_token_expiration}")
        # 5 days less
        refresh_token_expiration = (
            time_now
            + dt.timedelta(
                seconds=r.json()['refresh_token_expires_in'] - 432000))
        self.log.debug('Set refresh token expiration to '
                       f"{refresh_token_expiration}")

        self.credentials['access_token'] = r.json()['access_token']
        self.credentials['access_token_expiration'] = \
            access_token_expiration.strftime('%Y-%m-%d %H:%M:%S %Z%z')
        self.credentials['refresh_token'] = r.json()['refresh_token']
        self.credentials['refresh_token_expiration'] = \
            refresh_token_expiration.strftime('%Y-%m-%d %H:%M:%S %Z%z')
        self.credentials['token_type'] = r.json()['token_type']

        if save:
            self.log.debug(f"Saving credentials to {self.credentials_file}")
            FiddyHelper.save_credentials(section='TdaAmeritrade',
                                         file_=self.credentials_file,
                                         credentials=self.credentials)

        return '{} {}'.format(self.credentials['token_type'],
                              self.credentials['access_token'])


if __name__ == '__main__':
    tda_auth = TdaAuth()
    print(tda_auth.get_access_token())
