BASECOORDS = [40.440283, -3.689095];

function makeMap() {
    var TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    var MB_ATTR = 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
    mymap = L.map('llmap').setView(BASECOORDS, 8);
    L.tileLayer(TILE_URL, {attribution: MB_ATTR}).addTo(mymap);
}




$(document).ready(function(){
   
    makeMap();
    var socket = io.connect('http://' + document.domain + ':' + location.port + '/test');
    var layer = L.layerGroup();
    var heat = L.heatLayer([], {radius: 25}).addTo(mymap);
    //receive details from server
    socket.on('newcoord', function(msg) {
        console.log("lat: " + msg.lat + " lon: " + msg.lon + " rssi: " + msg.rssi);
        //maintain a list of ten numbers
        heat.addLatLng(L.latLng(msg.lat, msg.lon, msg.rssi))
    });

})