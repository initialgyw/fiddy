from typing import List
import numpy as np
import pandas as pd


def is_support(df_quotes, row):
    ''' 4 candle fractals for support '''
    return (df_quotes['low'][row] < df_quotes['low'][row - 1]
            and df_quotes['low'][row] < df_quotes['low'][row + 1]
            and df_quotes['low'][row + 1] < df_quotes['low'][row + 2]
            and df_quotes['low'][row - 1] < df_quotes['low'][row - 2])


def is_resistance(df_quotes, row):
    ''' 4 candle fractals for resistance '''
    return (df_quotes['high'][row] > df_quotes['high'][row - 1]
            and df_quotes['high'][row] > df_quotes['high'][row + 1]
            and df_quotes['high'][row + 1] > df_quotes['high'][row + 2]
            and df_quotes['high'][row - 1] > df_quotes['high'][row - 2])


def is_far_from_level(level, levels, avg_candle_size):
    return np.sum([abs(level - x) < avg_candle_size
                  for x in levels]) == 0


def get_avg_candle_size(df_quotes):
    return np.mean(df_quotes['high'] - df_quotes['low'])


def get_support_resistance(df_quotes) -> List[float]:
    ''' Shows the support and resistance

    Parameters
    ----------
    df_quotes : pd.DataFrame()

    Returns
    -------
    List[float]
    '''

    # determine the average candle size
    avg_candle_size = get_avg_candle_size(df_quotes)

    # clean up noise in levels
    levels = []
    for row in range(2, df_quotes.shape[0] - 2):
        if is_support(df_quotes, row):
            level = df_quotes['low'][row]

            if is_far_from_level(level, levels, avg_candle_size):
                levels.append((row, level))

        elif is_resistance(df_quotes, row):
            level = df_quotes['high'][row]

            if is_far_from_level(level, levels, avg_candle_size):
                levels.append((row, level))

    return sorted([level[1] for level in levels])


if __name__ == '__main__':
    from fiddy.tda import Tda
    from pprint import pprint
    tda = Tda()

    df_quotes = tda.get_daily_quotes('team')
    support_resistance = get_support_resistance(df_quotes)
    pprint(support_resistance)
