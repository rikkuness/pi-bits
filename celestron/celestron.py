import serial
import datetime
import ephem
import ephem.stars

DEG_TO_RAD = 0.0174532925

class ScopeNotFound(Exception):
   def __init__(self, value):
      self.value = value
   def __str__(self):
      return repr(self.value)

class Celestron(object):
   """Celestron API"""
   def __init__(self, port):
      super(Celestron, self).__init__()
      try:
         self.ser = serial.Serial(port, timeout=5)
      except serial.serialutil.SerialException:
         raise ScopeNotFound("Could not connect to telescope on port %s" % port)

   def _send(self, command):
      res = []
      self.ser.write(command)
      while True:
         this = self.ser.read()
         #print("%s => %s" % (this, type(this)))
         if this == '#':
            #print("%s => %s" % (command, res))
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

   def get_ra_dec(self, precise=False):
      if precise: data = self._send(b'e')
      else:       data = self._send(b'E')
      data = [chr(i) for i in data]
      
      if len(data) == 9:
         hex_ra   = ''.join(data[0:4])
         hex_dec = ''.join(data[5:9])

         ra    = int(hex_ra,  16) / 65536.0
         dec = int(hex_dec, 16) / 65536.0

      elif len(data) == 17:
         hex_ra   = ''.join(data[0:8])
         hex_dec = ''.join(data[9:17])

         ra    = int(hex_ra,  16) / 4294967296.0
         dec = int(hex_dec, 16) / 4294967296.0

      return ra * 360.0, dec * 360.0
      
   def get_alt_az(self, precise=False):
      if precise: data = self._send(b'z')
      else:       data = self._send(b'Z')
      data = [chr(i) for i in data]

      if len(data) == 9:
         hex_azm = ''.join(data[0:4])
         hex_alt =  ''.join(data[5:9])

         azm = int(hex_azm, 16) / 65536.0
         alt = int(hex_alt, 16) / 65536.0

      elif len(data) == 17:
         hex_azm = ''.join(data[0:8])
         hex_alt =  ''.join(data[9:17])

         azm = int(hex_azm,16) / 4294967296.0
         alt = int(hex_alt,16) / 4294967296.0
      
      return (
         ephem.degrees((alt * 360) * DEG_TO_RAD),
         ephem.degrees((azm * 360) * DEG_TO_RAD),
      )

   def get_location(self, unit='deg'):
      data = self._send(b'w')
      if len(data) == 8:
         if unit == 'deg':
            lat = self.dms2dd(*data[0:4])
            lon = self.dms2dd(*data[4:8])
         elif unit == 'dms':
            lat = data[0:4]
            lon = data[4:8]
         return (lat, lon)
      else:
         return None

   def get_target(self):
      alt, azm = self.get_alt_az(precise=True)
      lat, lon = self.get_location()

      variance = 0.025
      telescope = ephem.Observer()

      telescope.lat = lat * DEG_TO_RAD
      telescope.lon = lon * DEG_TO_RAD
      telescope.elevation = 63

      stars = []
      for star_name, star in ephem.stars.stars.items():
         star.compute(telescope)
         if star.alt - variance <= alt <= star.alt + variance:
            if star.az - variance <= azm <= star.az + variance:
               stars.append(star)
               return star

   def set_location(self, lat, lon):
      data = self.dd2dms(lat) + self.dd2dms(lon)
      data = b'W' + b''.join([chr(i) for i in data]) + b'#'
      self._send(data)
      self._send(b'')

   def get_time(self):
      data = self._send(b'h')
      self._send(b'')
      if len(data) == 8:
         try:
            dattime = datetime.datetime(
               2000 + data[5], 
               data[3], 
               data[4],
               *data[0:3])
            return dattime
         except:
            return None

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
