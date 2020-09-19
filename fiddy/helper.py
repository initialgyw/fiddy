from pathlib import Path
import pandas as pd
import configparser
import json
import pickle


class FiddyHelper:
    ''' Bunch of helper functions

    Methods
    -------
    load_credentials(file_) -> configparser.RawConfigParser
    save_credentials(file_, section, credentials) -> bool
    check_requests(requests, error_out) -> Tuple(bool, msg)
    save_data(file_, data, input_data_type)
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
                  input_data_type: str = None) -> bool:
        ''' Save the data to a file

        Parameters
        ----------
        file_: str
            location to save the data
        data: str, list, dict, df
            data to save
        data_type: type of data
            'lod' = list of dictionary
            'df' = dataFrame

        Returns
        -------
        True - if data is saved successfully

        '''

        # validate data
        if input_data_type == 'df':
            if not isinstance(data, pd.core.frame.DataFrame):
                raise ValueError('Provided data is not a dataframe')
            if data.empty:
                raise ValueError('Provided dataframe is empty')
        else:
            if not data:
                raise ValueError('Provided data is empty')

        # create parent directory if not exists
        Path(Path(file_).parent).mkdir(parents=True, exist_ok=True)

        if input_data_type == 'lod' or input_data_type == 'dict':
            # dump data as json
            if '.json' in file_:
                with open(file_, 'w') as f:
                    json.dump(data, f, indent=2)

        elif input_data_type == 'df':
            if '.csv' in file_:
                data.to_csv(file_)

        else:
            raise ValueError(f"Not sure how to save {input_data_type}")

        return True

    @staticmethod
    def load_data(file_: str,
                  output_data_type: str):
        ''' Load the data from file

        Parameters
        ----------
        file: str, required
            location of file to read
        data_type: str, required
            type of data being returned
                - df
                - lod
                - dict

        '''
        data = None

        # if file does not exists, return None
        if not Path(file_).exists():
            if output_data_type == 'df':
                return pd.DataFrame()

            return None

        if output_data_type == 'dict':
            if file_.endswith('.json'):
                with open(file_, 'r') as f:
                    data = json.loads(f.read())
            elif file_.endswith('.pickle'):
                data = pickle.load(open(file_, 'rb'))

        elif output_data_type == 'df':
            if '.csv' in file_:
                data = pd.read_csv(file_, index_col='Date', parse_dates=True)

        else:
            raise ValueError(f"Unknown data_type: {output_data_type}")

        return data
