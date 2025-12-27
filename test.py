import requests

data = {
  'From': '8004349271',
  'To': '6361949658',
  'CallerId': '07941056521'
}

requests.post('https://43233c08209735b3c9d15495a13a5946b6be1901c84cddf7:c3c0f3c86e1a8f10b1eaa76f7c4218e1482446ad3a32e288@api.exotel.com/v1/Accounts/drpathcare1/Calls/connect', data=data)


