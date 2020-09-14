from fiddy.tda import Tda
import requests
import json

tda = Tda()


def get_profile(symbol: str) -> None:
    ''' Get profile for chatbot '''

    symbol = symbol.upper()
    data = {}

    # get quote
    quote = tda.get_quotes(symbol)
    if not quote:
        return

    if quote[symbol]['assetType'] == 'MUTUAL_FUND':
        data['quote'] = quote[symbol]['closePrice']
    else:
        data['quote'] = quote[symbol]['mark']

    profile = tda.get_profile(symbol)
    data['description'] = profile['description']
    try:
        data['dividend_date'] = \
            profile['fundamental']['dividendDate'].split()[0]
    except IndexError:
        data['dividend_date'] = None

    try:
        data['dividend_pay_date'] = \
            profile['fundamental']['dividendDate'].split()[0]
    except IndexError:
        data['dividend_pay_date'] = None

    data['market_cap'] = profile['fundamental']['marketCap']

    message = f'''{symbol} ({data['description']})
    Quote: ${data['quote']}
    Market Cap: ${int(data['market_cap'])}
    Dividend Date: {data['dividend_date']}
    Dividend Pay Date: {data['dividend_pay_date']}
    '''

    return message


def rocketchatbot(ticker: str,
                  url: str,
                  channel: str,
                  request_header: dict):

    message = get_profile(ticker)

    url = f"https://{url}/api/v1/chat.postMessage"
    headers = request_header
    headers['Content-type'] = 'application/json'
    payload = {
        'channel': channel,
        'text': message
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    print(r.json())


if __name__ == '__main__':
    print(get_profile('aapl'))
