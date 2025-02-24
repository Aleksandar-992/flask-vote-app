import os
import random
import json
import socket
import logging

from datetime import datetime
from flask import Flask, request, make_response, render_template
from flask_sqlalchemy import SQLAlchemy

# Конфигурирање на логирањето
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

dbhost = os.environ.get('DB_HOST', '')
dbport = os.environ.get('DB_PORT', '')
dbname = os.environ.get('DB_NAME', '')
dbuser = os.environ.get('DB_USER', '')
dbpass = os.environ.get('DB_PASS', '')
dbtype = os.environ.get('DB_TYPE', '')

if dbtype in ['mysql', 'postgresql']:
    dburi = f"{dbtype}://{dbuser}:{dbpass}@{dbhost}:{dbport}/{dbname}"
else:
    dburi = f"sqlite:///{os.path.join(basedir, 'data/app.db')}"

app.config['SQLALCHEMY_DATABASE_URI'] = dburi
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db = SQLAlchemy(app)

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    question = db.Column(db.String(90))
    stamp = db.Column(db.DateTime, default=datetime.utcnow)
    options = db.relationship('Option', backref='poll', lazy='dynamic')

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(30))
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'))
    votes = db.Column(db.Integer, default=0)

def load_seed_data():
    try:
        with open('seeds/seed_data.json') as f:
            seed_data = json.load(f)
        
        for poll_data in seed_data['polls']:
            poll = Poll(name=poll_data['name'], question=poll_data['question'])
            db.session.add(poll)
            db.session.flush()  # Се додадени во базата за да добиеме poll.id
            
            for option_data in poll_data['options']:
                option = Option(text=option_data['text'], poll_id=poll.id)
                db.session.add(option)
        
        db.session.commit()
        app.logger.info("Seed data loaded successfully.")
    except Exception as e:
        app.logger.error(f"Error loading seed data: {e}")

@app.route('/')
@app.route('/index.html')
def index():
    try:
        hostname = socket.gethostname()
        poll = Poll.query.first()
        return render_template('index.html', hostname=hostname, poll=poll)
    except Exception as e:
        app.logger.error(f"Error in index: {e}")
        return "An error occurred", 500

@app.route('/vote.html', methods=['POST', 'GET'])
def vote():
    try:
        hostname = socket.gethostname()
        poll = Poll.query.first()
        
        if not poll:  # Проверка за 'None'
            app.logger.error("No polls found.")
            return "No polls available", 404  # Враќање на порака за грешка
        
        has_voted = False
        vote_stamp = request.cookies.get('vote_stamp')

        if request.method == 'POST':
            has_voted = True
            vote = request.form.get('vote')
            if vote and vote_stamp:
                app.logger.info(f"Vote received: {vote} from client with vote_stamp: {vote_stamp}")
            else:
                app.logger.warning("Vote stamp or vote is missing.")

            voted_option = Option.query.filter_by(poll_id=poll.id, id=vote).first()
            if voted_option:
                voted_option.votes += 1
                db.session.commit()
                app.logger.info(f"Vote recorded for option: {vote}")
            else:
                app.logger.error(f"Invalid vote option: {vote}")

        options = Option.query.filter_by(poll_id=poll.id).all()
        resp = make_response(render_template('vote.html', hostname=hostname, poll=poll, options=options))
        
        if has_voted:
            vote_stamp = hex(random.getrandbits(64))[2:-1]
            app.logger.info("Set cookie for voted")
            resp.set_cookie('vote_stamp', vote_stamp)
        
        return resp
    except Exception as e:
        app.logger.error(f"Error in vote: {e}")
        return "An error occurred", 500

@app.route('/results.html')
def results():
    try:
        hostname = socket.gethostname()
        poll = Poll.query.first()
        
        if not poll:  # Проверка за 'None'
            app.logger.error("No polls found.")
            return "No polls available", 404  # Враќање на порака за грешка

        results = Option.query.filter_by(poll_id=poll.id).all()
        return render_template('results.html', hostname=hostname, poll=poll, results=results)
    except Exception as e:
        app.logger.error(f"Error in results: {e}")
        return "An error occurred", 500


if __name__ == '__main__':
    try:
        db.create_all()  # Оваа линија ќе создаде табелите
        load_seed_data()  # Повикај ја функцијата за вчитување на податоците
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        app.logger.error(f"Error during application startup: {e}")




