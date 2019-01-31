
from flask_socketio import SocketIO, emit #Para manejar el socket
from flask import Flask, render_template, url_for, copy_current_request_context, jsonify #Flask es un framework web ligero, se usa para servir las páginas
import time
from threading import Thread, Event
from flask_sqlalchemy import SQLAlchemy #Manejo de base de datos, usamos sqlite
from SX127x.LoRa import * #Manejo del módem
from SX127x.board_config import BOARD
import random
import os
import struct #Para descodificar los mensajes recibidos
import atexit

import eventlet #Sin esto no es posible conectar a los sockets en la raspberry
eventlet.monkey_patch()


#Configuraciones varias
project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "points.db"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file

app.config['SECRET_KEY'] = 'wsnwsnwsn'
app.config['DEBUG'] = True

db = SQLAlchemy(app) #Instancia del objeto de la DB

BOARD.setup()
BOARD.reset()


#turn the flask app into a socketio app
socketio = SocketIO(app)

#random number Generator Thread
thread = Thread()
thread_stop_event = Event()

"""
Clase que maneja el módem SX1276
Hereda de la clase LoRa de la biblioteca SX127x
"""
class mylora(LoRa):
    #Método __init__ redefinido para que cuando se instancie un objeto mylora se configure automáticamente
    #Configuración de canal, coding rate, ancho de banda y spreading factor igual que la placa transmisora
    #Sólo se usa la capa LoRa, no la LoRaWAN, los mensajes son broadcast en el canal
    def __init__(self, verbose=False):
        super(mylora, self).__init__(verbose)
        self.set_freq(868.1)
        self.set_dio_mapping([0] * 6)
        self.received_new=0
        self.latLon =[]
        self.payload = ""
        self.set_pa_config(pa_select=1, max_power=21, output_power=15)
        self.set_bw(BW.BW125)
        self.set_coding_rate(CODING_RATE.CR4_8)
        self.set_spreading_factor(12)
        self.set_rx_crc(True)
        self.set_low_data_rate_optim(True)
        assert(self.get_agc_auto_on() == 1)

    #Método on_rx_done de la clase LoRa redefinido
    #Imprime el último mensaje recibido por consola y sube la bandera received_new de nuevo mensaje
    #Esta biblioteca maneja, además de la interfaz SPI, otras salidas del módem que alertan de finalización de transmisión, p. ej.
    def on_rx_done(self):
        self.clear_irq_flags(RxDone=1)
        self.payload = self.read_payload(nocheck=True)
        print ("Receive: ")
        print(bytes(self.payload).decode("utf-8",'ignore')) # Receive DATA
        self.received_new = 1

    #Devuelve el último mensaje y baja la bandera de nuevo mensaje recibido
    def get_last_message(self):
        self.received_new = 0
        return self.payload

    def get_rssi(self):
        return self.get_pkt_rssi_value()
    
    def msg_ready(self):
        return self.received_new
 
"""
Hilo que se ejecuta continuamente en background
Consulta periódicamente si hay mensaje nuevo recibido por LoRa
"""
class LoRaThread(Thread):
    def __init__(self):
        self.delay = 1
        super(LoRaThread, self).__init__()
        self.lora = mylora(verbose=False) #Instancia un objeto mylora que maneja el módem

    def loraListener(self):
        print("LoRa thread")
        while not thread_stop_event.isSet():
            if self.lora.msg_ready(): #Si hay mensaje nuevo recogemos su valor
                payload = self.lora.get_last_message()
                _lat, _lon = struct.unpack('ff', payload) #Son dos floats empaquetados como 4+4 bytes, los extraemos
                _rssi = self.lora.get_pkt_rssi_value()
                _snr = self.lora.get_pkt_snr_value()
                print("lat: ")
                print(_lat)
                print(" lon: ")
                print("\r\n")
                #Emitimos por el socket /test un objeto newcoord con la información del nuevo paquete
                #Se recibe dinámicamente en el navegador
                socketio.emit('newcoord', {'lat': float(_lat), 'lon': float(_lon), 'rssi': _rssi, 'snr': _snr}, namespace='/test')
                #Se guarda el punto obtenido en la base de datos
                point = Ping(id=int(time.time()), lat=_lat, lon=_lon, rssi=_rssi, snr=_snr)
                db.session.add(point)
                db.session.commit()
                #Se duerme el hilo hasta la siguiente activación
                time.sleep(self.delay)
    
    def shutdown(self):
        self.lora.set_mode(SLEEP)

    def run(self):
        self.loraListener()


"""
Modelo de Ping en la base de datos
Cada paquete que se reciba se guarda en forma de una entrada con esta estructura
Definido pero no se ha implementado el manejo
"""
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

"""
Función que devuelve la página principal cuando se accede a la raíz del servidor
El aspecto de la página depende de la plantilla index.html
Cuando se accede aquí se abre el socket
"""
@app.route('/')
def index():
    return render_template('index.html')

"""
Función que devuelve todos los puntos guardados en la base de datos en forma de json
No implementado aún lo que se hará con ellos
"""
@app.route('/getpoints')
def getpoints(district_id):
    points = Point.query.all()
    coords = [[point.lat, point.lon, point.rssi] for point in points]
    return jsonify({"data": coords})

"""
Cuando se conecte el navegador a la ruta /test se arranca el hilo del módem
"""
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

"""
Aviso de desconexión del cliente
"""
@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')

#Función para desconectar el módem y cerrar el hilo que lo maneja al cerrar el programa
def closing_function():
    LoRaThread.shutdown()
    BOARD.teardown()
    thread.join()
#Register the function to be called on exit
atexit.register(closing_function)

if __name__ == '__main__':
    socketio.run(app)