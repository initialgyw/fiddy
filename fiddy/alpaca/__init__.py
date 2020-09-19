from fiddy.helper import FiddyHelper
from fiddy.logger import logger
from pathlib import Path
from pytz import timezone
import datetime as dt
import alpaca_trade_api

tz = timezone('US/Eastern')


class Alpaca:
    ''' Alpaca API wrapper of wrapper

    Attributes
    ----------
    log: logging.Logger
    api: alpaca_trade_api.REST
    data_dir: str

    Methods
    -------
    get_calendar(cache) -> list
    get_credentials(file_, section) -> dict
    '''
    def __init__(self,
                 api_key_id: str,
                 secret_key: str,
                 base_url: str,
                 data_dir: str = f"{Path.home()}/fiddy/alpaca",
                 verbose: int = 3) -> None:
        ''' Initialize the Alpaca Class '''
        self.log = logger('Alpaca', verbose=verbose)
        self.api = alpaca_trade_api.REST(api_key_id,
                                         secret_key,
                                         base_url=base_url)
        self.data_dir = data_dir

    # ########
    # Calendar
    # ########
    def get_calendar(self,
                     cache: bool = True) -> list:
        ''' Get Calendar '''
        file_ = f"{self.data_dir}/calendar.json"
        data: dict = {}

        # load from cache if possible
        if cache:
            try:
                data = FiddyHelper.load_data(file_=file_,
                                             output_data_type='dict')
            except Exception as err:
                self.log.warning(err)
                pass

            if (data
                    and (dt.datetime.strptime(data['expiration'],
                                              '%Y-%m-%d').date()
                         > dt.datetime.now(tz).date())):
                self.log.debug(f"Read calendar from cache: {file_}")
                return data['calendar']
            else:
                self.log.debug('Calendar data expired. Acquiring new calendar')

        # at this point, new data is required
        market_hours: list = self.api.get_calendar()

        # market_hours return Alpaca Calendar class
        # converting to use readable format is easier
        calendar = [day._raw for day in market_hours]

        # organize data to save, set data expiration in 7 days
        data = {
            # set data expiration at +7 days
            'expiration': str((dt.datetime.now(tz)
                               + dt.timedelta(days=7)).date()),
            'calendar': calendar
        }

        FiddyHelper.save_data(file_=file_, input_data_type='dict', data=data)
        self.log.debug(f"Calendar saved to {file_}\n"
                       f"Calendar data expiration: {data['expiration']}")

        return calendar

    def get_calendar_dt(self) -> list:
        ''' Get calendar in datetime format

        Returns
        -------
        List[Dict]
            {'market_close': datetime.datetime(
                    2029, 12, 24, 13, 0,
                    tzinfo=<DstTzInfo 'US/Eastern' LMT-1 day, 19:04:00 STD>),
             'market_open': datetime.datetime(
                    2029, 12, 24, 9, 30,
                    tzinfo=<DstTzInfo 'US/Eastern' LMT-1 day, 19:04:00 STD>),
             'session_close': datetime.datetime(
                    2029, 12, 24, 23, 59, 59,
                    tzinfo=<DstTzInfo 'US/Eastern' LMT-1 day, 19:04:00 STD>),
             'session_open': datetime.datetime(
                    2029, 12, 24, 0, 0, 1,
                    tzinfo=<DstTzInfo 'US/Eastern' LMT-1 day, 19:04:00 STD>)}
        '''

        file_ = f"{self.data_dir}/calendar.pickle"
        calendar: list = FiddyHelper.load_data(file_=file_,
                                               output_data_type='dict')

        # ensure data is not expired
        if calendar and (dt.datetime.now(tz).date() < calendar['expiration']):
            self.log.debug(f"Read calendar from {file_}")
            return calendar['calendar']

        # make str of calendar easy to use
        calendar: list = self.get_calendar()
        calendar_dt: list = []
        for cal in calendar:
            date = dt.datetime.strptime(cal['date'], '%Y-%m-%d')
            market_open = date.replace(hour=int(cal['open'].split(':')[0]),
                                       minute=int(cal['open'].split(':')[1]),
                                       tzinfo=tz)
            market_close = date.replace(hour=int(cal['close'].split(':')[0]),
                                        minute=int(cal['close'].split(':')[1]),
                                        tzinfo=tz)
            session_open = date.replace(hour=0, minute=0, second=1, tzinfo=tz)
            session_close = date.replace(hour=23, minute=59, second=59,
                                         tzinfo=tz)

            calendar_dt.append({
                'market_open': market_open,
                'market_close': market_close,
                'session_open': session_open,
                'session_close': session_close
            })

        # save the data
        data = {
            'expiration': str((dt.datetime.now(tz)
                               + dt.timedelta(days=1)).date()),
            'calendar': calendar_dt
        }
        FiddyHelper.save_data(file_=file_, data=data, input_data_type='dict')
        self.log.debug(f"Saved calendar in datetime formats to {file_}")

        return calendar_dt

    def get_last_closing_date(self,
                              time_=dt.datetime.now(tz),
                              extended_hours: bool = False) -> dt.date:
        ''' Get last closing date or business date

        Parameters
        ----------
        time_ : datetime or datetime.dt
            the start of the lookup
        calendar: list
            list of dictionaries for market hours
        extended_hours: bool
            include extend_hours as current session

        Returns
        -------
        dt.date
        '''

        # get calendar in datetime format
        calendar = self.get_calendar_dt()

        if type(time_) == dt.date:
            # Arbitrarily set the hours and minute as 18:00 for regular hour
            # and 23:59:59 as extended hour if time was not passed in
            if extended_hours is False:
                time_ = tz.localize(dt.datetime.combine(time_,
                                                        dt.time(18, 0, 0)))
            else:
                time_ = tz.localize(dt.datetime.combine(time_,
                                                        dt.time(23, 59, 59)))

        elif (type(time_) == dt.datetime
              and time_.strftime('%H:%M') == '00:00'):
            if extended_hours is False:
                time_ = time_.replace(hour=18, minute=0)
            else:
                time_ = time_.replace(hour=23, minute=59, second=59)
        self.log.debug(f"VAR: time_ = {str(time_)}")

        if extended_hours is False:
            closing_hours = [cal['market_close']
                             for cal in calendar
                             if cal['market_close'] < time_][-1]
        else:
            closing_hours = [cal['session_close']
                             for cal in calendar
                             if cal['session_close'] < time_][-1]

        return closing_hours.date()

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
    creds = Alpaca.get_credentials()
    alpaca = Alpaca(creds['api_key_id'],
                    creds['secret_key'],
                    base_url=creds['base_url'])

    # calendar
    # calendar = alpaca.get_calendar()

    # get_calendar_dt
    # calendar = alpaca.get_calendar_dt()
    # print(calendar[-1])

    # time_ = dt.datetime.now(tz)
    time_ = dt.datetime(2020, 9, 17, 0, 0, 0, tzinfo=tz)
    last_closing_date = alpaca.get_last_closing_date(time_=time_,
                                                     extended_hours=False)
    print(last_closing_date)
