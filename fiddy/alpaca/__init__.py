from fiddy.helper import FiddyHelper
from pathlib import Path


class Alpaca:
    ''' Alpaca API wrapper of wrapper

    Attributes
    ----------

    Methods
    -------
    '''

    @staticmethod
    def get_credentials(file_: str = f"{Path.home()}/.fiddy.ini",
                        section: str = 'alpaca_paper') -> dict:
        ''' Get Alpaca credentials from an INI file
        See README.md for more info

        Parameters
        ----------
        file_ : str
            absolute path of the INI file
        section : str
            INI section name

        Returns
        -------
        {'api_key_id': <str>,
         'secret_key': <str>,
         'base_url: <str>}
        '''

        credentials: dict = {}
        credentials_ini = FiddyHelper.load_credentials(file_)

        for key in ['api_key_id', 'secret_key', 'base_url']:
            credentials[key] = credentials_ini[section][key]

        return credentials


if __name__ == '__main__':
    print(Alpaca.get_credentials())
