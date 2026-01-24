import flask
from flask import request, jsonify, Response, Flask, render_template, redirect
from flask_restful import Resource, Api, marshal_with
from flask_socketio import SocketIO, emit, send
from threading import Thread
import time
import ast
import requests
from requests.auth import HTTPBasicAuth
import getpass
import json
import os.path
import sys
import logging
import re

app = flask.Flask(__name__)
app.config["DEBUG"] = True

# SocketIO
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')
thread = None
clients = []

revealedStories = []

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# angular calls this
@app.route('/api/socket')
def index():
    logger.info('Route socket init')
    return ('{"ok":"success"}')


#Function that runs when a clients get connected to the server
@socketio.on('connect')
def test_connect():
    global clients
    clients.append(request.sid)
    logger.info('Client connected {0}'.format(request.sid))

@socketio.on('send-show-poker-results')
def send_show_poker_results(message):
    logger.info('received show_poker_results {0} from {1}'.format(message, request.sid))
    logger.info('sending Data to {0} clients'.format(clients))

    if message['storyKey'] not in revealedStories:
        revealedStories.append(message['storyKey'])

    # broadcast to all but self
    for client in clients:
        if client != request.sid:
            emit('show-poker-results', message, room=client)

@socketio.on('send-hide-poker-results')
def send_hide_poker_results(message):
    logger.info('received hide_poker_results {0} from {1}'.format(message, request.sid))
    logger.info('sending Data to {0} clients'.format(clients))

    if message['storyKey'] in revealedStories:
        revealedStories.remove(message['storyKey'])
        clear_votes_for_story(message['storyKey'])

    # broadcast to all but self
    for client in clients:
        if client != request.sid:
            emit('hide-poker-results', message, room=client)

@socketio.on('disconnect')
def test_disconnect():
    global clients
    clients.remove(request.sid)
    logger.info('Client disconnected')

# Rest APIs
data_storage_filename = 'data/data.json'
poker_config_filename = 'src/assets/poker-config.json'
api_config_filename = 'data/api-config.json'
is_demo_mode = False

# Check if api-config.json exists in data/, otherwise use demo/
if not os.path.isfile(api_config_filename):
    logger.info('data/api-config.json not found, using demo mode')
    is_demo_mode = True
    data_storage_filename = 'demo/data.json'

users = []
config = {}

jiraUsername = ''
jiraPassword = ''

# read userdata from storage
if os.path.isfile(data_storage_filename):
    with open(data_storage_filename) as data_storage_file:
        data_storage = data_storage_file.read()
        if (data_storage):
            users = ast.literal_eval(data_storage)

# Read api-config.json only if not in demo mode
if not is_demo_mode:
    logger.info('Reading config from ' + api_config_filename)
    with open(api_config_filename) as f:
        config = ast.literal_eval(f.read())
        if 'jiraUsername' in config:
            jiraUsername = config['jiraUsername']
        if 'jiraPassword' in config:
            jiraPassword = config['jiraPassword']

logger.info('Reading config from ' + poker_config_filename)
with open(poker_config_filename) as f:
    api_config = ast.literal_eval(f.read())
    config = {**config, **api_config}

#logger.info(json.dumps(config))

# get jira username and password
if jiraUsername and jiraPassword:
    logger.info('Configured jira User: ' + jiraUsername)
else:
    logger.info('Please add Authentication for jira at ' + poker_config_filename)

# cleanup outdated stories from storage file when story is not at pokerlist but in storage file
def cleanup_storage():
    logger.info('Cleanup storage file now!')
    logger.info('old list: ' + json.dumps(users))
    current_storylist = []
    for story in get_pokerlist_from_jira():
        current_storylist.append(story['key'])
    logger.info('Current stories: ' + json.dumps(current_storylist))
    if len(current_storylist) > 0:
        for user in users:
            if 'stories' in user:
                clean_list = list(filter(lambda userstory: userstory['key'] in current_storylist, user['stories']))
                user['stories'] = clean_list
    logger.info('new list after cleanup: ' + json.dumps(users))
    save_file()

def clear_votes_for_story(storyKey):
    for user in users:
        if 'stories' in user:
            clean_list = list(filter(lambda userstory: userstory['key'] != storyKey, user['stories']))
            user['stories'] = clean_list

@app.route('/', methods=['GET'])
def home():
    return '<p>Here is nothing.</p>'

@app.route('/jira-proxy/<path:path>', methods=['GET'])
def jira_proxy(path):
    # allow only proxy of attachments
    if jiraPassword and jiraUsername and re.compile(config['backend-proxy-path-regex']).match(path):
        # load
        proxyDict = {}
        if 'proxy' in config:
            http_proxy  = config['proxy']
            https_proxy = http_proxy
            ftp_proxy   = http_proxy
            logger.info('set proxy to ' + http_proxy)
            proxyDict = {
                "http"  : http_proxy,
                "https" : https_proxy,
                "ftp"   : ftp_proxy
            }

        jiraResponse = requests.get(config['jiraUrl'] + path, auth=(jiraUsername, jiraPassword), proxies=proxyDict)
        excluded_headers = ['cache-control', 'content-type']
        headers = [(name, value) for (name, value) in jiraResponse.raw.headers.items()
                   if name.lower() in excluded_headers]

        return Response(jiraResponse.content, jiraResponse.status_code, headers)
    # simple redirect -> fallback
    return redirect(config['jiraUrl'] + path, code=302)

@app.route('/api/users/all', methods=['GET'])
def api_all_users():
    results = []
    for user in users:
        if 'username' in user:
            results.append(user['username'])
    return jsonify(results)

@app.route('/api/users/updateStory', methods=['POST'])
def api_update_story():
    data = request.get_json()
    if 'username' not in data:
        return Response("{msg:'username missing'}", status=400, mimetype='application/json')
    if 'storyKey' not in data and 'note' not in data:
        return Response("{msg:'storyKey or note missing'}", status=400, mimetype='application/json')
    for user in users:
        if user['username'] == data['username']:
            if 'stories' not in user:
                # no stories found, create new array
                user['stories'] = []
            # search for story to update
            filteredStories = list(filter(lambda story: story['key'] == data['storyKey'], user['stories']))
            if len(filteredStories) == 0:
                # no story found, create new one
                new_properties = {}
                if 'storyPoints' in data:
                    new_properties.update({'points': data['storyPoints']})
                if 'note' in data:
                    new_properties.update({'note': data['note']})
                if 'isNotePrivate' in data:
                    new_properties.update({'isNotePrivate': data['isNotePrivate']})
                new_properties.update({'key': data['storyKey']})
                user['stories'] += [new_properties]
            elif len(filteredStories) == 1:
                if 'storyPoints' in data:
                    filteredStories[0]['points'] = data['storyPoints']
                if 'note' in data:
                    filteredStories[0]['note'] = data['note']
                if 'isNotePrivate' in data:
                    filteredStories[0]['isNotePrivate'] = data['isNotePrivate']
            else:
                return Response("{msg:'multiple story keys found'}", status=400, mimetype='application/json')
            if 'storyPoints' in data:
                socketio.emit('update-active-poker-users', {'storyKey': data['storyKey'], 'activePokerUsers': get_active_poker_users(data['storyKey'])})
    save_file()
    return Response("{msg:'updated storyPoints list'}", status=201, mimetype='application/json')

def save_file():
    with open(data_storage_filename, 'w') as f:
        f.write(str(users))

@app.route('/api/users/add', methods=['POST'])
def api_add():
    data = request.get_json()
    if 'username' in data:
        newUsername = data['username']
        if len([user for user in users if user['username'] == newUsername]) > 0:
            return Response("{error:'user already exists'}", status=400, mimetype='application/json')
        else:
            users.append({'username': newUsername})
            with open(data_storage_filename, 'w') as f:
                f.write(str(users))
            return Response("{msg:'created user with name " + newUsername + "'}", status=201, mimetype='application/json')
    else:
        return Response("{error:'no username given'}", status=400, mimetype='application/json')

@app.route('/api/users', methods=['POST'])
def api_id():
    # Create an empty list for our results
    results = []
    data = request.get_json()

    if 'username' in data:
        # Loop through the data and match results that fit the requested ID.
        # IDs are unique, but other fields might return many results
        for user in users:
            if user['username'] == data['username']:
                results.append(user)

        if (len(results) > 0):
            # Use the jsonify function from Flask to convert our list of
            # Python dictionaries to the JSON format.
            response = jsonify(results)
            response.status_code  = 200
            return response
            #return jsonify(results)
        else:
            return Response("{error:'no user found with name " + data['username'] + "'}", status=400, mimetype='application/json')
    else:
        return Response("{error:'no username given'}", status=400, mimetype='application/json')

@app.route('/api/jira/pokerresults', methods=['POST'])
def show_poker_results():
    data = request.get_json()
    if 'storyKey' in data:
        pokerListResult = []
        for user in users:
            userStoryPoints = get_story_points_for_user(user['username'], data['storyKey'])
            # check if user has story points or a public note
            if userStoryPoints and ('points' in userStoryPoints or 'note' in userStoryPoints and ('isNotePrivate' not in userStoryPoints or userStoryPoints['isNotePrivate'] == False)):
                userResult = {"username": user['username'], "storyPoints": userStoryPoints['points']}
                if 'note' in userStoryPoints and ('isNotePrivate' not in userStoryPoints or userStoryPoints['isNotePrivate'] == False):
                    userResult.update({'note': userStoryPoints['note']})
                pokerListResult.append(userResult)
    return jsonify(pokerListResult)

def get_active_poker_users(story_key):
    active_poker_users = []
    for user in users:
        userStoryPoints = get_story_points_for_user(user['username'], story_key)
        if userStoryPoints and 'points' in userStoryPoints:
            active_poker_users.append(user['username'])
    return active_poker_users

def get_story_points_for_user(username, storyKey):
    for user in users:
        if 'username' in user and username == user['username']:
            if 'stories' in user:
                for story in user['stories']:
                    if story['key'] == storyKey and 'points' in story:
                        return story
            return ''
    return ''

@app.route('/api/jira/pokerlist', methods=['GET'])
def jira_pokerlist():
    return jsonify(get_pokerlist_from_jira())

def get_pokerlist_from_jira():
    jiraStoryAttributesWhiteList = ['key', 'summary', 'description']
    if not is_demo_mode:
        # load
        proxyDict = {}
        if 'proxy' in config:
            http_proxy  = config['proxy']
            https_proxy = http_proxy
            ftp_proxy   = http_proxy
            logger.info('set proxy to ' + http_proxy)
            proxyDict = {
                "http"  : http_proxy,
                "https" : https_proxy,
                "ftp"   : ftp_proxy
            }

        jiraResponse = requests.post(config['jiraUrl'] + 'rest/api/2/search', json = {'jql': config['jiraPokerListJql'], "expand": ["renderedFields"], "fields": jiraStoryAttributesWhiteList}, headers={"Content-Type": "application/json", "Accept" : "application/json"},auth=(jiraUsername, jiraPassword), proxies=proxyDict)
        jsonResponse = json.loads(jiraResponse.text)
    else:
        # mock jiraResponse
        mock_search_file = 'demo/search.json'
        logger.info('mock jira pokerlist from ' + mock_search_file)
        with open(mock_search_file) as json_file:
            jsonResponse = json.load(json_file)

    resultList = []
    if 'issues' in jsonResponse:
        for issue in jsonResponse["issues"]:
            resultIssueElement = {}
            # iterate all required attributes and write to new json for response
            for issueAttributeKey in jiraStoryAttributesWhiteList:
                if issueAttributeKey in issue and issue[issueAttributeKey] is not None:
                    resultIssueElement[issueAttributeKey] = issue[issueAttributeKey]
                elif issueAttributeKey in issue['renderedFields'] and issue['renderedFields'][issueAttributeKey] is not None:
                    resultIssueElement[issueAttributeKey] = issue['renderedFields'][issueAttributeKey]
                elif issueAttributeKey in issue['fields']:
                    resultIssueElement[issueAttributeKey] = issue['fields'][issueAttributeKey]
                else:
                    logger.info('Could not find attribute {0} at jira response.'.format(issueAttributeKey))
            resultIssueElement['revealed'] = resultIssueElement['key'] in revealedStories
            resultIssueElement['activePokerUsers'] = get_active_poker_users(resultIssueElement['key'])
            resultList.append(resultIssueElement)
        return resultList
    else:
        return []

def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    """Handler for unhandled exceptions that will write to the logs"""
    if issubclass(exc_type, KeyboardInterrupt):
        # call the default excepthook saved at __excepthook__
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_unhandled_exception

cleanup_storage()

#This is the function that will create the Server in the ip host and port 5000
if __name__ == "__main__":
    logger.info("starting webservice")
    socketio.run(app, host='0.0.0.0', debug=False)

