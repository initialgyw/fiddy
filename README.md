# fiddy
Get Rich or Die Tryin'

## Configuration
### ~/.fiddy.ini
```
[APN RocketChat]
username = <str>
password = <str>
url = <str>

[Robinhood]
username = <str>
password = <str>
two_fa_secret = <str>

[alpaca_paper]
api_key_id = <str>
secret_key = <str>
base_url = https://paper-api.alpaca.markets

[alpaca_live]
api_key_id = <str>
secret_key = <str>
base_url = https://api.alpaca.markets

[TdaAmeritrade]
username = <str>
password = <str>
consumer_key = <str>
redirect_uri = <str>
```

## Notes
### Tda
* When authenticating TDA, at the point where the webdriver browser is asking for 2FA, you have 30 seconds to type the code and check remember device. DO NOT click continue.