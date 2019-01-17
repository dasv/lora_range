
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)
app = Flask(__name__)

class Ping(db.Model)
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    rssi = db.column(db.Integer)
    snr = db.column(db.Integer)
    
    def __init__(self, id, lat, lon, rssi, snr)
        self.id = id
        self.lat = lat
        self.lon = lon
        self.rssi = rssi
        self.snr = snr

    @property
    def strength(self)
        return null

@app.route('/')
def hello_world():
        return 'Hello, World!'
