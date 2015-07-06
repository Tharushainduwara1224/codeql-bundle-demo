"""
This API interacts with a user and token database.
The code is written to exemplify common API security vulnerabilities 
1. No input validation
2. SQL queries are not parameterized
3. No real error handling
4. Errors that are handled give too much information
4. Tokens have an expiration date, but do not expire
5. Token string is generated with an md5 of the expire datetime string
6. Passwords are not hashed in the database
7. There is an *undocumented* GET that returns the user database
"""

import sqlite3
import json
import hashlib
import time
from bottle import route, run, request, debug


@route('/tokens', method='POST')
def get_token():
    '''
    User needs to get an auth token before actioning the database
    '''
    data = request.json
    username = data['auth']['passwordCredentials']['username']
    password = data['auth']['passwordCredentials']['password']
    conn = sqlite3.connect('vAPI.db')
    c = conn.cursor()
    # no data validation
    # no sql parameterization
    user_query = "SELECT * FROM users WHERE username = '%s' AND password = '%s'" % (username, password)
    c.execute(user_query)
    user = c.fetchone()
    response = {}
    if user:
        response['access'] = {}
        response['access']['user'] = {'id': user[0], 'name': user[1]}
        # make sure to get most recent token in database, because we arent removing them... 
        token_query = "SELECT * FROM tokens WHERE userid = '%s' ORDER BY expires DESC" % (user[0])
        c.execute(token_query)
        token_record = c.fetchone()
        if type(token_record) == tuple:
            if token_record[3] < int(time.time()):
                # token has expired. create new one that expires 5 minutes after creation
                expire_stamp = int(time.time()+300)
                expire_date = time.ctime(int(expire_stamp))
                token = hashlib.md5(expire_date).hexdigest()
                # we'll parameterize this one because we need this serious functionality
                c.execute('INSERT INTO tokens (token, userid, expires) VALUES (?, ?, ?)', (token, user[0], expire_stamp))
                response['access']['token'] = {'id': token, 'expires': expire_date}
                conn.commit()
                conn.commit()
            else:
                # recent token hasn't expired. use same one. 
                expire_date = time.ctime(int(token_record[3]))
                response['access']['token'] = {'id': token_record[1], 'expires': expire_date}
        else:
            # no token exists. create one that expires in 5 minutes
            expire_stamp = int(time.time()+300)
            expire_date = time.ctime(int(expire_stamp))
            token = hashlib.md5(expire_date).hexdigest()
            # we'll parameterize this one because we need this serious functionality
            c.execute('INSERT INTO tokens (token, userid, expires) VALUES (?, ?, ?)', (token, user[0], expire_stamp))
            response['access']['token'] = {'id': token, 'expires': expire_date}
    else:
        # let's do another look up so we can return helpful info for failure cases
        c.execute("SELECT * FROM users WHERE username = '%s'" % username)
        user = c.fetchone()
        if user:
            response['error'] = {'message': 'password does not match'}
        else:
            response['error'] = {'message': 'username ' + username + ' not found'}
    conn.close()
    return {json.dumps(response)}

@route('/tokens', method='GET')
def get_get_token():
    '''
    this is an undocumented request. EASTER EGG
    /tokens is only supposed to accept a POST! Are you checking the other verbs?
    '''
    conn = sqlite3.connect('vAPI.db')
    c = conn.cursor()
    query = "SELECT * FROM users"
    c.execute(query)
    users = c.fetchall()
    return {'response': users}

@route('/user/<user:re:.*>', method='GET')
def get_user(user):
    '''
    Expects a user id to return that user's data.
    X-Auth-Token is also expected
    '''
    token = request.headers.get('X-Auth-Token')
    conn = sqlite3.connect('vAPI.db')
    c = conn.cursor()
    user_query = "SELECT * FROM users WHERE id = '%s'" % (user)
    c.execute(user_query)
    user_record = c.fetchone()
    token_query = "SELECT * FROM tokens WHERE token = '%s'" % (str(token))
    c.execute(token_query)
    token_record = c.fetchone()
    c.close()
    response = {}
    if type(token_record) == tuple:
        if type(user_record) == tuple:
            if token_record[2] == user_record[0]:
                response['user'] = {}
                response['user']['id'] = user_record[0]
                response['user']['name'] = user_record[1]
                response['user']['password'] = user_record[2]
            else:
                response['error'] = {'message': 'the token and user do not match!'}
        else:
            response['error'] = {'message': 'user id ' + user + ' not found'}
    else:
        response['error'] = {'message': 'token id ' + str(token) + ' not found'}
    conn.close()
    return {'response': response}

debug(True)
run(port=8081, reloader=True)