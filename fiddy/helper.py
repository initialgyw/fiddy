from pathlib import Path
import configparser


class FiddyHelper:
    ''' Bunch of helper functions

    Methods
    -------
    load_credentials(file_)
    '''

    @staticmethod
    def load_credentials(file_) -> configparser.RawConfigParser:
        ''' Loads the credential INI file

        Parameters
        ----------
        file_ : str
            location of the INI file

        Returns
        -------
        configparser.RawConfigParser

        Exceptions
        ----------
        FileNotFoundError
        '''
        # ensure file exist
        if not Path(file_).exists():
            raise FileNotFoundError(f"{file_} does not exist")

        credentials: configparser.RawConfigParser = \
            configparser.RawConfigParser()
        credentials.read(file_)

        return credentials

    @staticmethod
    def save_credentials(file_: str,
                         section: str,
                         credentials: dict):
        ''' Save the credentials into file '''

        # load the existing credentials
        loaded_credentials = FiddyHelper.load_credentials(file_)

        # add section if it doesn't exist
        try:
            loaded_credentials.add_section(section)
        except configparser.DuplicateSectionError:
            pass

        # store key and value to section
        for key, value in credentials.items():
            loaded_credentials[section][key] = value

        with open(file_, 'w') as f:
            loaded_credentials.write(f)

        return

    @staticmethod
    def check_requests(r, error_out: bool = False):
        ''' Check requests

        Parameters
        ----------
        r : requests
        error_out : bool
            raise Exception if non-200

        Returns
        -------
        bool

        Exceptions
        ----------
        RequestError
        '''
        from fiddy.exceptions import RequestError

        msg = f"{r.request.method} to {r.request.url} returned " \
              f"{r.status_code}"

        if r.status_code != 200:
            if error_out:
                raise RequestError(msg)
            else:
                return False, msg

        return True, msg
