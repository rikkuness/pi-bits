#!/usr/bin/env python
import curses
import gps
import sys, time, logging, re
from pprint import pprint
import PyIndi

telescope_name = 'Celestron NexStar 130SLT'
camera_name = 'Canon EOS 100D'
gps_name = 'GPS'

data = {}
messages = []

gps_session = gps.gps()


class IndiClient(PyIndi.BaseClient):
	telescope = None
	camera = None
	gps = None

	def __init__(self):
		super(IndiClient, self).__init__()
		self.logger = logging.getLogger('PyQtIndi.IndiClient')
		logMessage('Creating an instance of PyQtIndi.IndiClient')

	def handleNumber(self, p):
		num = p.getNumber()[0]
		if hasattr(num, 'nvp'):
			for i in num.nvp:
				data[p.getDeviceName()][i.name] = i.value
		else:
			data[p.getDeviceName()][num.name] = num.value

	def handleText(self, p):
		txt = p.getText()[0]
		data[p.getDeviceName()][txt.name] = txt.text

	def handleSwitch(self, p):
		sw = p.getSwitch()[0]
		data[p.getDeviceName()][sw.name] = sw.s

	def newDevice(self, d):
		data[d.getDeviceName()] = {}
		if not d.isConnected():
			logMessage("Connecting to "+d.getDeviceName())
			self.connectDevice(d.getDeviceName())

	def newProperty(self, p):
		if p.getType() == PyIndi.INDI_TEXT:
			self.handleText(p)
		elif p.getType() == PyIndi.INDI_NUMBER:
			self.handleNumber(p)
		elif p.getType() == PyIndi.INDI_SWITCH:
			self.handleSwitch(p)
		elif p.getType() == PyIndi.INDI_LIGHT:
			pass
			#logMessage("Found a light property...")
		elif p.getType() == PyIndi.INDI_BLOB:
			pass
			#logMessage("Found a blob property...")
		else:
			pass
			#logMessage("unhandled type for "+p.getDeviceName())

	def newNumber(self, n):
		if hasattr(n, 'nvp'):
			for i in n.np.nvp:
				data[n.device][i.name] = i.value
		else:
			data[n.device][n.name.decode()] = n.np.value			

	def newSwitch(self, s):
		data[s.device][s.name.decode()] = s.sp.s
	def newText(self, t):
		#print dir(t)
		data[t.device][t.name.decode()] = t.s
	def newBLOB(self, b):
		#logMessage("Found a new blob...")
		pass
	def newLight(self, b):
		#logMessage("Found a new light...")
		pass
	def newMessage(self, d, m):
		logMessage(re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}: ', '', d.lastMessage()))
	def removeProperty(self, p):
		logMessage("Removed property "+p.name)
	def serverConnected(self):
		logMessage("Server connected ("+self.getHost()+":"+
			str(self.getPort())+")")
	def serverDisconnected(self, code):
		logMessage("Server disconnected (exit code = "+str(code)+
			","+str(self.getHost())+":"+str(self.getPort())+")")

class CursesWindow(object):
	def __enter__(self):
		self.stdscr = curses.initscr()
		self.stdscr.immedok(True)
		curses.cbreak()
		curses.noecho()

		#COLORS
		curses.start_color()
		curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
		curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
		curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
		curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)

		return self.stdscr

	def __exit__(self,a,b,c):
		curses.nocbreak()
		curses.echo()
		curses.endwin()

# Curses Screens
def gpsScreen():
	window_gps = curses.newwin(10,35,0,0)
	window_gps.box()
	
	# Title
	dev = indiclient.getDevice(gps_name)
	if dev and dev.isConnected(): gps_status = 2
	else: gps_status = 4
	window_gps.addstr(0, 2, gps_name, curses.color_pair(gps_status))

	# Tuple of heading name and property name
	headings = [
		("UTC Time", "UTC"),
		("Status", "GPS_FIX"),
		("Lattitude", "LAT"),
		("Longitude", "LONG"),
		("Elevation", "ELEV"),
	]

	gps_session.query('ados')
	window_gps.addstr(2, 2, "Status")
	window_gps.addstr(2, 14, gps_session.fix.time)
	
#	for i, heading in enumerate(headings):
#		window_gps.addstr(i+2, 2, heading[0])
#		if gps_name in data.keys():
#			status = 1
#			val = str(data[gps_name].get(heading[1],'-'))
#			if heading[1] == "GPS_FIX":
#				if val == "NO FIX": status = 4
#				elif val == "3D FIX": status = 2
#
#			window_gps.addstr(i+2, 14, val, curses.color_pair(status))

	# Redraw
	window_gps.refresh()

def mountScreen():
	window_mount = curses.newwin(10,35,10,0)
	window_mount.box()

	# Title
	dev = indiclient.getDevice(telescope_name)
	if dev and dev.isConnected(): telescope_status = 2
	else: telescope_status = 4
	window_mount.addstr(0, 2, telescope_name, curses.color_pair(telescope_status))

	# Tuple of heading name and property name
	headings = [
		("UTC Time", "UTC"),
		("Eq. RA", "RA"),
		("Eq. Dec", "DEC"),
		("Parking", "TELESCOPE_PARK"),
	]

	for i, heading in enumerate(headings):
		window_mount.addstr(i+2, 2, heading[0])
		if telescope_name in data.keys():
			window_mount.addstr(i+2, 14, str(data[telescope_name].get(heading[1],'-')))

	# Redraw
	window_mount.refresh()

def cameraScreen():
	window_ccd = curses.newwin(20,25,0,35)
	window_ccd.box()

	# Title
	dev = indiclient.getDevice(camera_name)
	if dev and dev.isConnected(): camera_status = 2
	else: camera_status = 4
	window_ccd.addstr(0, 2, camera_name, curses.color_pair(camera_status))

	# Tuple of heading name and property name
	headings = [
		("Battery", "batterylevel"), 
		("Capacity", "availableshots"),
		("Exposure", "CCD_EXPOSURE_VALUE"),
		("Max X", "CCD_MAX_X"),
		("Max Y", "CCD_MAX_Y"),
		("Temp", "colortemperature"),
	]

	for i, heading in enumerate(headings):
		window_ccd.addstr(i+2,2, heading[0])
		if camera_name in data.keys():
			window_ccd.addstr(i+2, 14, str(data[camera_name].get(heading[1], '-')))

	# Redraw
	window_ccd.refresh()

def messagesScreen():
	window_messages = curses.newwin(20,60,20,0)
	window_messages.box()
	
	# Title
	window_messages.addstr(0, 2, "Messages", curses.color_pair(2))

	# Render messaged to screen
	for i, msg in enumerate(messages):
		window_messages.addstr(i+2, 2, str(msg))

	window_messages.refresh()

# Add a message to the display
def logMessage(message):

	# Add timestamp
	message = "%s %s" % (time.strftime("%H:%M:%S", time.gmtime()), message)

	# Drop messages from end of list to prevent overflow
	if len(messages) > 15: del messages[0]

	# Concat message to prevent wrapping
	if len(message) > 53: message = message[0:53] + "..."

	messages.append(message)

# Try to reconnect disconnected devices
def retryDisconnected():
	for d in indiclient.getDevices():
		if not d.isConnected():
			logMessage("Retrying connection to "+d.getDeviceName())
			indiclient.connectDevice(d.getDeviceName())
			if d.isConnected():
				logMessage("Connection to %s succeeded!" % d.getDeviceName())

def syncSiteData():
	telescope = indiclient.getDevice(telescope_name)
	if telescope and telescope.isConnected():
		logMessage("telescope is connected, doing a sync")

# Main function
def main():
	indiclient.setServer("localhost", 7624)

	# Init the retry timer
	last_connect = time.time()
	
	# Open curses screen
	with CursesWindow() as screen:

		# Could not contact INDI server on start
		while (not(indiclient.connectServer())):
			screen.clear()
			screen.box()
			screen.addstr(12, 21, "COULD NOT CONNECT", curses.color_pair(1))
			screen.move(0,0)
			time.sleep(1)

		# Main loop
		while True:
			screen.clear()
			
			# Retry any disconnected devices
			if (time.time() - last_connect) > 10:
				#syncSiteData()
				retryDisconnected()
				last_connect = time.time()

			# Update all curses windows
			gpsScreen()
			mountScreen()
			cameraScreen()
			messagesScreen()

			time.sleep(0.5)

if __name__ == "__main__":
	indiclient = IndiClient()
	main()
