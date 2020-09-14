from pathlib import Path
import pandas as pd
import configparser
import json


class FiddyHelper:
    ''' Bunch of helper functions

    Methods
    -------
    load_credentials(file_)
    save_credentials(file_, section, credentials)
    check_request(request, error_out)
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

    @staticmethod
    def save_data(file_: str,
                  data=None,
                  data_type: str = None) -> bool:
        '''Save the data to a file

        Parameters
        ----------
        file_: str, required
            location to save the data
        data: str, list, dict, df, required
            data to save
        data_type: type of data
            'lod' = list of dictionary
            'df' = dataFrame

        Returns
        -------
        True - if data is saved successfully

        Exceptions
        ----------
        TypeError
            - if data_type == df and data is not dataframe
            - Unknown data_type
        ValueError
            - if data_type == df and data is empty
            - if data is empty
        '''

        # validate data
        if data_type == 'df':
            if not isinstance(data, pd.core.frame.DataFrame):
                raise TypeError('Provided data is not a dataframe')
            if data.empty:
                raise ValueError('Provided dataframe is empty')
        else:
            if not data:
                raise ValueError('Provided data is empty')

        # create parent directory if not exists
        Path(Path(file_).parent).mkdir(parents=True, exist_ok=True)

        if data_type == 'lod' or data_type == 'dict':
            # dump data as json
            if '.json' in file_:
                with open(file_, 'w') as f:
                    json.dump(data, f, indent=2)

        elif data_type == 'df':
            if '.csv' in file_:
                data.to_csv(file_)

        else:
            raise TypeError(f"Not sure how to save {data_type}")

        return True

    @staticmethod
    def load_data(file_: str,
                  data_type: str):
        '''Load the data from file

        Parameters
        ----------
        file: str, required
            location of file to read
        data_type: str, required
            type of data being returned
                - df
                - lod
                - dict

        Exceptions
        ----------
        TypeError
            - Unknown data_type
        '''
        data = None

        # if file does not exists, return None
        if not Path(file_).exists():
            if data_type == 'df':
                return pd.DataFrame()

            return None

        if data_type == 'dict':
            if '.json' in file_:
                with open(file_, 'r') as f:
                    data = json.loads(f.read())

        elif data_type == 'df':
            if '.csv' in file_:
                data = pd.read_csv(file_, index_col='Date', parse_dates=True)
        else:
            raise TypeError(f"Unknown data_type to load: {data_type}")

        return data