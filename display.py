#!/usr/bin/env python
import os, sys
import curses
import time
import threading
from datetime import datetime
import dateutil.parser
import ephem
from gps import *
from celestron.celestron import Celestron

tty = "/dev/ttyUSB1"
display_width = 80
display_height = 26

data = {
	'telescope':{
		'display':None,
	},
	'messages':{
		'display':None,
		'logs':[]
	},
	'gps':{
		'display':None
	}
}

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

class CursesWindow(object):
	def __enter__(self):
		self.stdscr = curses.initscr()
		self.stdscr.immedok(True)
		curses.cbreak()
		curses.noecho()
		self.stdscr.keypad(1)
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
		self.stdscr.keypad(0)

def clear_area(window, start_x, start_y, end_x, end_y):
	for x in range(start_x, end_x):
		for y in range(start_y, end_y):
			window.addstr(x, y, ' ')
	window.refresh()

def messages_screen():
	window = data['messages']['display']
	if not window:
		data['messages']['display'] = curses.newwin(10,display_width,16,0)
		window = data['messages']['display']
		window.box()
		window.addstr(0, 2, "Messages", curses.color_pair(2))
	else:
		clear_area(window, 1, 1, 8, display_width - 2)

	for i, msg in enumerate(data['messages']['logs']):
		window.addstr(i+1, 2, str(msg))

	window.refresh()

def telescope_screen(info):
	window = data['telescope']['display']
	if not window:
		data['telescope']['display'] = curses.newwin(16,50,0,0)
		window = data['telescope']['display']
		window.box()
		window.addstr(0, 2, "Telescope", curses.color_pair(2))
	else:
		clear_area(window, 1, 1, 5, 48)
	if 'lat' in info.keys() and 'lon' in info.keys():
		window.addstr(1,2,"Lat     %s" % info['lat'])
		window.addstr(2,2,"Long    %s" % info['lon'])

	if 'time' in info.keys(): 
		window.addstr(3,2,"UTC     %s" % info['time'].strftime("%Y-%m-%d %H:%M:%S"))

	if 'target' in info.keys():
		window.addstr(4,2,"Target  %s" % info['target'])

	if 'alt' in info.keys() and 'azm' in info.keys():
		window.addstr(5,2,"Alt     %s" % info['alt'])
		window.addstr(6,2,"Azm     %s" % info['azm'])
	window.refresh()

def gps_screen(info):
	window = data['gps']['display']
	if not window:
		data['gps']['display'] = curses.newwin(16,30,0,50)
		window = data['gps']['display']
		window.box()
		window.addstr(0, 2, "GPS", curses.color_pair(2))

	window.addstr(1,2,"Lat   %s" % info['lat'])
	window.addstr(2,2,"Long  %s" % info['lon'])
	window.addstr(3,2,"UTC   %s" % info['time'].strftime("%Y-%m-%d %H:%M:%S"))

	window.refresh()

# Add a message to the display
def log_message(message):

	# Add timestamp
	message = "%s %s" % (time.strftime("%H:%M:%S", time.gmtime()), message)

	# Drop messages from end of list to prevent overflow
	if len(data['messages']['logs']) > 7: del data['messages']['logs'][0]

	# Concat message to prevent wrapping
	if len(message) > display_width - 7:
		message = message[0:display_width - 7] + "..."

	data['messages']['logs'].append(message)

# Main function
def main():
	global gpsp
	refresh_rate = 0.5

	gpsp = GpsPoller()
	try:
		gpsp.start()
	except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
		print "\nKilling Thread..."
		gpsp.running = False
		gpsp.join() # wait for the thread to finish what it's doing

	telescope = Celestron(tty)
	if telescope: log_message("Connected to telescope via serial.")

	telescope_data = {}

	# Open curses screen
	with CursesWindow() as screen:

		# Main loop
		while True:

			lat_lon = telescope.get_location()
			if lat_lon:
				telescope_data['lat'] = lat_lon[0]
				telescope_data['lon'] = lat_lon[1]

			tel_time = telescope.get_time()
			if tel_time: telescope_data['time'] = tel_time

			target = telescope.get_target()
			if target:
				if target.name != telescope_data.get('target',''):
					log_message("New targetted star '%s'" % target.name)
				telescope_data['target'] = target.name
			else: telescope_data['target'] = '-'

			azm_alt = telescope.get_alt_az()
			if azm_alt:
				telescope_data['alt'] = azm_alt[0]
				telescope_data['azm'] = azm_alt[1]

			gpsdata = {
				'lat':	gpsd.fix.latitude,
				'lon':	gpsd.fix.longitude,
				'time':	dateutil.parser.parse(gpsd.utc)
			}

			# Update all curses windows
			telescope_screen(telescope_data)
			gps_screen(gpsdata)
			messages_screen()

			time.sleep(refresh_rate)

if __name__ == "__main__":
	main()
	gpsp.running = False