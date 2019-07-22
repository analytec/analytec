#!/usr/bin/python3
#test
from flask import *
import twitterdata
import csv_utils
from csv_utils import *
import os
from werkzeug.utils import secure_filename
from flask_basicauth import BasicAuth
import creds
from celery import Celery

def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'], broker=app.config['CELERY_BROKER_URL'], redis_max_connections=20, BROKER_TRANSPORT_OPTIONS = {'max_connections': 20}, broker_pool_limit=None)
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://h:p3d0a7931cedd1aa7795041e34c1f69e67531c4df8317678103cacfce841df440@ec2-52-1-169-125.compute-1.amazonaws.com:12809',
    CELERY_RESULT_BACKEND='redis://h:p3d0a7931cedd1aa7795041e34c1f69e67531c4df8317678103cacfce841df440@ec2-52-1-169-125.compute-1.amazonaws.com:12809'
)

celery_app = make_celery(app)

app.config['BASIC_AUTH_USERNAME'] = creds.auth_token_penult
app.config['BASIC_AUTH_PASSWORD'] = creds.auth_token_prelim
app.config['BASIC_AUTH_FORCE'] = True
basic_auth = BasicAuth(app)

import engine # don't change this line's placement!

@app.route('/', methods=['GET', 'POST'])
@basic_auth.required
def home():
    error=None
    if request.method == 'POST':
        error=None
        file = request.files['file']
        filename = secure_filename(file.filename)
        file.save(os.path.join('csv/', filename))

    return render_template('home.html', error=error)

@app.route('/help', methods=['GET', 'POST'])
def help():
    return render_template('help.html')

@app.route('/dashboard/<data>', methods=['GET', 'POST'])
def dashboard(data):
    usernames = list(eval(data).keys())
    username_count = len(usernames)
    div_size = username_count*20 + 10
    return render_template('dashboard.html', usernames = usernames, data = eval(data), div_size=div_size)

@app.route('/taskstatus_bulk/<task_id>')
def taskstatus_bulk(task_id):
    task = engine.twitter_bulk_query_wad.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
        }
        try:
            if 'result' in task.info:
                data = {}
                response['result'] = task.info['result']
                for element in task.info['result']:
                    for key in element:
                        data[key] = element[key]
                print("ALL DATA SO FAR: ")
                print(data)
                response['url'] = url_for('dashboard', data=data)
                return jsonify(response)
        except Exception as e: # this commonly throws an error, as the result may not yet be returned; we'll ignore it here
            print(e)
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
        }
    return jsonify(response)


@app.route('/loading_bulk', methods=['GET', 'POST'])
def loading_bulk():
    error=None
    if request.method == 'POST':
        error=None
        processor_count = int(request.form['processor-count-bulk'])
        try:
            tweets_num = int(request.form['tweets-num-bulk'])
            print('User has selected number of tweets as ' + str(tweets_num))
        except Exception as e:
            return render_template('home.html', errorcsv="Please select a valid number of tweets.")
        try:
            selected_file = request.files['file']
        except Exception as e:
            return render_template('home.html', errorcsv='Please select a CSV file to use.')
        filename = secure_filename(selected_file.filename)
        if filename.endswith(".csv") == False:
            error = "Please select a .csv file!"
            return render_template('home.html',errorcsv=error)
        else:
            selected_file.save(os.path.join('csv/', filename))

        usernames = list(csv_to_list('csv/' + filename))
        print(usernames)
        try:
            task = engine.twitter_bulk_query_wad.delay(user_list=usernames, tweets_num=tweets_num, threads=processor_count)
        except Exception as e:
            print(e)
            return render_template('home.html', errorcsv=str(e))
        username_count = len(usernames)
        div_size = username_count*20 + 10
        return render_template('loading.html', status_url=url_for('taskstatus_bulk', task_id = task.id), tweets_num=(tweets_num * username_count), processor_count=processor_count)

@app.route('/taskstatus_single/<task_id>')
def taskstatus_single(task_id):
    task = engine.concurrent_twitter_query_wad.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
        }
        try:
            if 'result' in task.info:
                response['result'] = task.info['result']
                username = list(task.info['result'].keys())[0]
                response['url'] = url_for('tw_graph', username = username, data=response['result'][username])
                print(response)
                return jsonify(response)
        except Exception as e:
            print("taskstatus_single():")
            print(e)
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
        }
    return jsonify(response)

@app.route('/loading_single', methods=['GET', 'POST'])
def loading_single():
    if request.method == 'POST':
        error=None
        username = str(request.form['username-tw'])
        try:
            tweets_num = int(str(request.form['tweets-num-single']))
            processor_count = int(request.form['processor-count-single'])
        except Exception as e:
            return render_template('home.html', error="Please enter a valid number of tweets and a valid processor count.")
        if not username:
            error = "Please enter a username before searching!"
            return render_template('home.html', error=error)
        try:
            task = engine.concurrent_twitter_query_wad.delay(username, tweets_num=tweets_num, threads=processor_count)
        except Exception as e:
            print(e)
            return render_template('home.html', error=str(e))
        return render_template('loading.html', status_url=url_for('taskstatus_single', task_id = task.id), tweets_num=tweets_num, processor_count=processor_count)

@app.route('/tw_graph/<username>/<data>', methods=['GET', 'POST'])
def tw_graph(username, data):
    data = eval(data)
    print(data)
    x_vals = engine.gen_list(len(data['weapons']))
    print('WEAPON MAX: ' + str(max(data['weapons'])))
    print('DRUGS MAX: ' + str(max(data['drugs'])))
    print('ALCOHOL MAX: ' + str(max(data['alcohol'])))

    return render_template(
        'tw_graph.html',
        name = username,
        tweets_num = len(data['weapons']),
        drug_vals = data['drugs'],
        drug_max = max(data['drugs']),
        weapon_vals = data['weapons'],
        weapon_max = max(data['weapons']),
        alcohol_vals = data['alcohol'],
        alcohol_max = max(data['alcohol']),
        x_vals = x_vals
    )

if __name__ == '__main__':
    app.run(debug=True, host='localhost',port=8080)
