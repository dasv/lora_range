BASECOORDS = [40.440283, -3.689095]; //Centro del mapa en el CEI

function makeMap() { //Función estándar de inicializado de mapa de la biblioteca Leaflet
    var TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    var MB_ATTR = 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
    mymap = L.map('llmap').setView(BASECOORDS, 8);
    L.tileLayer(TILE_URL, {attribution: MB_ATTR}).addTo(mymap);
}




$(document).ready(function(){//Función de JQuery
   
    makeMap(); //Inicializa el mapa
    var socket = io.connect('http://' + document.domain + ':' + location.port + '/test'); //Se conecta al socket
    var layer = L.layerGroup();
    var heat = L.heatLayer([], {radius: 25}).addTo(mymap); //Se crea la capa del heatmap
    //Recibe mensajes del servidor
    socket.on('newcoord', function(msg) {
        console.log("lat: " + msg.lat + " lon: " + msg.lon + " rssi: " + msg.rssi); //Saca el contenido del paquete por consola de debug
        //maintain a list of ten numbers
        heat.addLatLng(L.latLng(msg.lat, msg.lon, msg.rssi)) //Se añade el punto al heatmap
    });

})