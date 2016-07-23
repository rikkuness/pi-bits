import serial
from time import sleep
import datetime
import threading
from gps import *
import dateutil.parser
import ephem

gpsd = None
gpsp = None

class GpsPoller(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
      global gpsd
      gpsd = gps(mode=WATCH_ENABLE)
      self.current_value = None
      self.running = True
 
   def run(self):
      global gpsd
      while gpsp.running:
         gpsd.next()

class Celestron(object):
   """Celestron API"""
   def __init__(self, port):
      super(Celestron, self).__init__()
      self.ser = serial.Serial(port, timeout=1)

   def _send(self, command):
      res = []
      self.ser.write(command)
      while True:
         this = self.ser.read()
         #print("%s => %s" % (this, type(this)))
         if this == '#':
            #print("res => %s" % res)
            return res
         elif this:
            res.append(ord(this))
         else:
            return
   
   def dms2dd(self, degrees, minutes, seconds, direction):
      dd = float(degrees) + float(minutes)/60 + float(seconds)/(60*60);
      if direction == 1: dd *= -1
      return dd

   def dd2dms(self, deg):
      d = int(deg)
      md = abs(deg - d) * 60
      m = int(md)
      sd = int((md - m) * 60)
      di = 0
      if d < 0:
         d *= -1
         di = 1
      return [d, m, sd, di]

   def get_precise_ra_dec(self):
      data = self._send(b'e')
      ra, dec = ''.join(data).split(',')
      ra = (int(ra, 16) / 16777216) * 360
      dec = (int(dec, 16) / 16777216) * 360

      return (ra, dec)

   def get_ra_dec(self):
      data = self._send(b'E')
      

   def get_location(self):
      data = self._send(b'w')
      if len(data) == 8:
         lat = self.dms2dd(*data[0:4])
         lon = self.dms2dd(*data[4:8])
         return (lat, lon)
      else:
         print data
         return None

   def set_location(self, lat, lon):
      data = self.dd2dms(lat) + self.dd2dms(lon)
      data = b'W' + b''.join([chr(i) for i in data]) + b'#'
      self._send(data)
      self._send(b'')

   def get_time(self):
      data = self._send(b'h')
      if len(data) == 8:
         return datetime.datetime(
            2000 + data[5], 
            data[3], 
            data[4],
            *data[0:3])
   def set_time(self, gps_time):
      data = b'H' + b''.join([
         chr(gps_time.hour),
         chr(gps_time.minute),
         chr(gps_time.second),
         chr(gps_time.month),
         chr(gps_time.day),
         chr(gps_time.year - 2000),
         chr(0), chr(0)
         ])
      self._send(data)
      self._send(b'')

gpsp = GpsPoller()
try:
   gpsp.start()
except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
   print "\nKilling Thread..."
   gpsp.running = False
   gpsp.join() # wait for the thread to finish what it's doing

cel = Celestron('/dev/ttyUSB2')

print("Waiting for GPS lock.")
while gpsd.fix.mode == 1:
   sleep(0.1)
print("GPS lock found!")

print("Setting location.")
cel.set_location(gpsd.fix.latitude, gpsd.fix.longitude)
print(cel.get_location())

print("Setting time.")
cel.set_time(dateutil.parser.parse(gpsd.utc))
print(cel.get_time())


gpsp.running = False