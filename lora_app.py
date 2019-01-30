
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, url_for, copy_current_request_context, jsonify
import time
from threading import Thread, Event
from flask_sqlalchemy import SQLAlchemy
#from SX127x.LoRa import *
#from SX127x.board_config import BOARD
import random
import os
import struct

import eventlet
eventlet.monkey_patch()



project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "points.db"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file

app.config['SECRET_KEY'] = 'ordidro'
app.config['DEBUG'] = True

db = SQLAlchemy(app)

#BOARD.setup()
#BOARD.reset()


#turn the flask app into a socketio app
socketio = SocketIO(app)

#random number Generator Thread
thread = Thread()
thread_stop_event = Event()

"""
class RandomThread(Thread):
    def __init__(self):
        self.delay = 1
        super(RandomThread, self).__init__()

    def randomNumberGenerator(self):
        """
        Generate a random number every 1 second and emit to a socketio instance (broadcast)
        Ideally to be run in a separate thread?
        """
        #infinite loop of magical random numbers
        print("Making random numbers")
        while not thread_stop_event.isSet():
            latLon = [0, 0]
            latLon[0] = random.uniform(40.441, 40.437)
            latLon[1] = random.uniform(-3.687, -3.691)
            _rssi = random.uniform(0,1)
            point = Ping(lat=latLon[0], lon=latLon[1], rssi=_rssi, snr=0, id=int(time.time()))
            db.session.add(point)
            db.session.commit()
            print(latLon)
            socketio.emit('newcoord', {'lat': latLon[0], 'lon': latLon[1], 'rssi': _rssi}, namespace='/test')
            time.sleep(self.delay)

    def run(self):
        self.randomNumberGenerator()
""" 
class mylora(LoRa):
    def __init__(self, verbose=False):
        super(mylora, self).__init__(verbose)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0] * 6)
        self.received_new=0
        self.latLon =[]
        self.payload = ""

    def on_rx_done(self):
        self.clear_irq_flags(RxDone=1)
        self.payload = self.read_payload(nocheck=True)
        print ("Receive: ")
        print(bytes(self.payload).decode("utf-8",'ignore')) # Receive DATA
        self.received_new = 1

    
    def get_last_message(self):
        self.received_new = 0
        return self.payload

    def get_rssi(self):
        return self.get_pkt_rssi_value()
    
    def msg_ready(self):
        return self.received_new
 
    
class LoRaThread(Thread):
    def __init__(self):
        self.delay = 1
        super(LoRaThread, self).__init__()
        self.lora = mylora(verbose=False)

    def startLoRa(self):
        self.lora.set_pa_config(pa_select=1, max_power=21, output_power=15)
        self.lora.set_bw(BW.BW125)
        self.lora.set_coding_rate(CODING_RATE.CR4_8)
        self.lora.set_spreading_factor(12)
        self.lora.set_rx_crc(True)
        self.lora.set_low_data_rate_optim(True)
        assert(self.lora.get_agc_auto_on() == 1)

    def loraListener(self):
        print("Making random numbers")
        while not thread_stop_event.isSet():
            if self.lora.msg_ready():
                payload = self.lora.get_last_message()
                _lat, _lon = struct.unpack('ff', payload)
                _rssi = self.lora.get_pkt_rssi_value()
                _snr = self.lora.get_pkt_snr_value()
                print("lat: ")
                print(_lat)
                print(" lon: ")
                print("\r\n")
                socketio.emit('newcoord', {'lat': float(_lat), 'lon': float(_lon), 'rssi': _rssi, 'snr': _snr}, namespace='/test')
                sleep(self.delay)

    def run(self):
        self.startLoRa()
        self.loraListener()



class Ping(db.Model):
    __table_args__ = {'sqlite_autoincrement': True}
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    rssi = db.Column(db.Integer)
    snr = db.Column(db.Integer)
    
    def __init__(self, id, lat, lon, rssi, snr):
        self.id = id
        self.lat = lat
        self.lon = lon
        self.rssi = rssi
        self.snr = snr

    @property
    def strength(self):
        return 0


@app.route('/')
def index():
    #only by sending this page first will the client be connected to the socketio instance
    return render_template('index.html')

@app.route('/getpoints')
def getpoints(district_id):
    points = Point.query.all()
    coords = [[point.lat, point.lon, point.rssi] for point in points]
    return jsonify({"data": coords})

@socketio.on('connect', namespace='/test')
def test_connect():
    # need visibility of the global thread object
    global thread
    print('Client connected')

    #Start the random number generator thread only if the thread has not been started before.
    if not thread.isAlive():
        print("Starting Thread")
        thread = RandomThread()
        thread.start()

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app)