-Run both scripts to simulate the two ends.
-Run them multiple times to simulate many servers and clients.
-Check the scripts to see how to run them.

For Proxy.py:
Run using command – python proxy.py [port number] [ip address]

If no port number and ip address are given, default port number 8080 and ip address 127.0.0.1 are taken.

1.)  Blacklisting – Initially we have blacklisted the localhost and geeksforgeeks site. Can be checked by inputing different id and pasword other than that listed in authorised users in proxy.py
2.) Authorisation – However the authorised person can access even the blacklisted sites. Authorised users are listen in proxy.py
3.) Cache – The requestes are cached if we ask the same request more than 3 times in 5 minutes.
4.) Error Handling – The errors are handled properly in blacklisting as well as other places.
