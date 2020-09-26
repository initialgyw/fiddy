from fiddy.logger import logger
from fiddy.helper import FiddyHelper
from fiddy.tda.auth import TdaAuth
from fiddy.alpaca import Alpaca
from pathlib import Path
from typing import List, Dict
from pytz import timezone
import pandas as pd
import datetime as dt
import requests
import time

tz = timezone('US/Eastern')


class Tda:
    ''' TDA Class

    Attributes
    ----------
    log
    auth
    url
    data_dir

    Methods
    -------
    get_price_history
    get_daily_quotes
    get_minute_quotes
    get_fundamentals
    '''
    def __init__(self,
                 username: str = None,
                 password: str = None,
                 consumer_key: str = None,
                 redirect_uri: str = None,
                 credentials_file: str = f"{Path.home()}/.fiddy.ini",
                 url: str = 'https://api.tdameritrade.com',
                 data_dir: str = f"{Path.home()}/fiddy/tda",
                 verbose: int = 3):
        ''' Initialize the Tda class '''

        self.log = logger(name='TDA', verbose=verbose)
        self.auth = TdaAuth(username=username,
                            password=password,
                            consumer_key=consumer_key,
                            redirect_uri=redirect_uri,
                            credentials_file=credentials_file,
                            verbose=verbose)
        self.url = url
        self.data_dir = data_dir

        # initialize alpaca
        alpaca_creds = Alpaca.get_credentials()
        self.alpaca = Alpaca(alpaca_creds['api_key_id'],
                             alpaca_creds['secret_key'],
                             alpaca_creds['base_url'])

        # calendar
        self.calendar = self.alpaca.get_calendar_dt()

    def _convert_time_to_epoch_ms(self, time_: dt.datetime):
        ''' Convert a datetime to epoch millsecond '''
        return int(time_.timestamp() * 1000)

    def get_fundamental(
            self,
            symbol: str,
            url: str = 'https://api.tdameritrade.com/v1/instruments'):
        ''' Get fundamentals for a ticker '''
        symbol = symbol.upper()

        file_ = f"{self.data_dir}/{symbol}/fundamental.json"
        
        # load from cache if possible
        fundamental_data = FiddyHelper.load_data(file_=file_,
                                                 output_data_type='dict')
        if (fundamental_data
                and (dt.datetime.now(tz).date()
                     < dt.datetime.strptime(
                            fundamental_data['expiration'],
                            '%Y-%m-%d').date())):
            self.log.debug(f"Read fundamental data from {file_}")
            return fundamental_data['fundamental']

        # build request
        headers = {'Authorization': self.auth.get_access_token()}
        payload = {
            'symbol': symbol,
            'projection': 'fundamental',
        }

        r = requests.get(url, headers=headers, params=payload)
        FiddyHelper.check_requests(r, error_out=True)

        if not r.json():
            self.log.warning(f"{symbol} does not exist in TDA")
            return None

        fundamental_data = {
            'expiration': str((dt.datetime.now(tz)
                               + dt.timedelta(days=1)).date()),
            'fundamental': r.json()[symbol]
        }
        FiddyHelper.save_data(file_=file_,
                              data=fundamental_data,
                              input_data_type='dict')
        self.log.debug(f"Saved fundamental's data to {file_}")
        
        return fundamental_data['fundamental']

    def get_price_history(
            self,
            symbol: str,
            period_type: str = 'year',
            period: int = 20,
            frequency_type: str = 'daily',
            frequency: int = 1,
            end_date: int = None,
            start_date: int = None,
            need_extended_hours_data: bool = True) -> List[Dict]:
        ''' Get Price History
            https://developer.tdameritrade.com/price-history/apis/get/marketdata/%7Bsymbol%7D/pricehistory
            by default, it gets 20 years of daily data

        Parameters
        ----------
        symbol: str, required
            A security ticker
        period_type: str, defaults to year
            day, month, year, or ytd
        period: int, defaults to 20
            how many period_types
        frequency_type: str, defaults to daily
            single candle data - daily, minute, weekly, monthly
        frequency: int, defaults to 1
            how many frequency_type
        end_date: int
            milliseconds since epoch
        start_date: int
            milliseconds since epoch
        need_extended_hours_data: bool, defaults = true
            Extended hours data

        Returns
        -------
        list of dict
             {'close': 279.1,
              'datetime': 1587013200000,
              'high': 280.03,
              'low': 275.76,
              'open': 279.15,
              'volume': 131798325},
             {'close': 286.64,
              'datetime': 1587099600000,
              'high': 287.3,
              'low': 282.4,
              'open': 285.38,
              'volume': 146684784}]
        '''
        from fiddy.exceptions import RequestError

        # variables validation
        symbol = symbol.upper()

        # build request
        headers = {'Authorization': self.auth.get_access_token()}
        payload = {
            'frequencyType': frequency_type,
            'frequency': frequency,
            'needExtendedHoursData': need_extended_hours_data
        }
        if start_date and end_date:
            payload['startDate'] = start_date
            payload['endDate'] = end_date
        else:
            payload['periodType'] = period_type
            payload['period'] = period

        url = f"{self.url}/v1/marketdata/{symbol}/pricehistory"

        # get the request
        rate_limit_counter = 0
        while rate_limit_counter < 3:
            if rate_limit_counter == 2:
                raise RequestError('Rate Limit Hit')

            self.log.debug(f"Getting quotes for {str(payload)}")
            r = requests.get(url, params=payload, headers=headers)
            _, msg = FiddyHelper.check_requests(r, error_out=False)

            if r.status_code == 429:
                self.log.warning('Hitting rate limit. Sleeping for 40 seconds.')
                rate_limit_counter = rate_limit_counter + 1
                time.sleep(40)
                continue
            elif r.status_code == 200:
                break
            else:
                raise RequestError(msg)

        if len(r.json()['candles']) == 0:
            self.log.debug(f"{symbol} returned no quotes with "
                           f"payload {payload}")

        return r.json()['candles']

    def get_daily_quotes(self,
                         symbol: str,
                         cache: bool = True) -> pd.core.frame.DataFrame:
        ''' Get daily quotes '''
        symbol = symbol.upper()
        file_ = f"{self.data_dir}/{symbol}/daily.csv"

        # load from cache if possible
        if cache:
            df_quotes = FiddyHelper.load_data(file_=file_,
                                              output_data_type='df')

            # validate data
            if not df_quotes.empty:
                last_epoch = df_quotes['datetime'].tail(1).values[0] / 1000

                if (dt.datetime.fromtimestamp(last_epoch).date()
                        == self.alpaca.get_last_closing_date(
                                            extended_hours=True)):
                    self.log.debug(f"Returned {symbol} daily quotes from "
                                   f"{file_}")
                    return df_quotes

        # make sure the symbol exists
        if not self.get_fundamental(symbol=symbol):
            raise ValueError(f"{symbol} does not exist in TDA")

        # get quotes
        quotes = self.get_price_history(symbol)

        # return empty dataframe if quotes is None
        if len(quotes) == 0:
            return pd.DataFrame()

        # convert to dataframe
        df_quotes = pd.DataFrame(quotes)

        # save the data to file
        FiddyHelper.save_data(file_=file_,
                              data=df_quotes,
                              input_data_type='df',
                              index=False)
        self.log.debug(f"Saved {symbol} daily quote into {file_}")

        return df_quotes

    def get_minute_quotes(self,
                          symbol: str,
                          start_day: dt.date = None,
                          end_day: dt.date = dt.datetime.now(tz).date(),
                          frequency: int = 1) -> pd.DataFrame():
        ''' Get and save minute quotes
        I can't think of a way to read and save daily quotes without
        referencing single days. This is fine but this will lead to API rate
        limiting.

        Parameters
        ----------
        symbol: str
            stock ticker
        start_day: dt.date
            beginning of the day for minutes quotes
        end_day: dt.date
            end of the day for minute quotes
        frequency: int
            1, 5, 10, 15, 30 - minutes, defaults to 1

        Returns
        -------
        pd.DataFrame
        '''
        symbol = symbol.upper()

        # make sure the symbol exists
        if not self.get_fundamental(symbol=symbol):
            raise ValueError(f"{symbol} does not exist in TDA")

        # if start_day is not provided, one year ago will be used
        if start_day is None:
            start_day = end_day - dt.timedelta(days=365)

        self.log.debug(f"VAR: start_day = {start_day}, end_day = {end_day}")

        # get the business days between start and end
        business_days = [day
                         for day in self.calendar
                         if (day['session_open'].date() >= start_day
                             and day['session_open'].date() <= end_day)]

        # get the quotes per day
        df_quotes = pd.DataFrame()
        for day in business_days:
            
            date = day['session_open'].date()

            # used for reading and saving data
            file_ = f"{self.data_dir}/{symbol}/" \
                    f"{str(date)}-{frequency}minute.csv"

            # used to check if minute data exist for that date
            file_no_data = f"{file_}-NODATA"
            if Path(file_no_data).exists():
                self.log.debug(f"{file_no_data} exists. "
                               f"No {frequency} minute data on {date}")
                continue

            # load from cache
            df_quote = FiddyHelper.load_data(file_=file_,
                                             output_data_type='df')
            if not df_quote.empty:
                self.log.debug(f"Read {symbol} {frequency}-minute data "
                               f"from {file_}")
                df_quotes = df_quotes.append(df_quote)
                continue

            # tda takes in epoch time
            day_start_epoch = self._convert_time_to_epoch_ms(
                                day['session_open'])
            day_end_epoch = self._convert_time_to_epoch_ms(day['session_close'])

            quotes = self.get_price_history(symbol,
                                            start_date=day_start_epoch,
                                            end_date=day_end_epoch,
                                            frequency=frequency,
                                            frequency_type='minute')
            
            # no quotes detected, meaning tda is not returning anything
            if len(quotes) == 0:
                FiddyHelper.save_data(file_=file_no_data,
                                      data='NONE',
                                      input_data_type='NONE')
                self.log.debug(f"Created {file_no_data} "
                               "so it's not queried again")
                continue

            # convert to dataframe
            df_quote = pd.DataFrame(quotes)

            # if day is today don't save
            if (date != dt.datetime.now(tz).date):
                # save the data to file
                FiddyHelper.save_data(file_=file_,
                                      data=df_quote,
                                      input_data_type='df',
                                      index=False)
                self.log.debug(f"Saved {symbol} {frequency}-minute quotes "
                               f"into {file_}")

            # append it df_quotes
            df_quotes = df_quotes.append(df_quote)

        return df_quotes

if __name__ == '__main__':
    tda = Tda()
    # df_quotes = tda.get_daily_quotes('spy')
    # print(df_quotes)

    # minute quotes
    df_quotes = tda.get_minute_quotes('tsla')
    print(df_quotes)

    # fundamental
    # tda.get_fundamental('spy')