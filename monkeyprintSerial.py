# -*- coding: latin-1 -*-
#
#	Copyright (c) 2022-2023 GEM UNICAMP
#	Distributed under the GNU GPL v2.
#
#	This file is part of monkeyprint.
#
#	monkeyprint is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	monkeyprint is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You have received a copy of the GNU General Public License
#    along with monkeyprint.  If not, see <http://www.gnu.org/licenses/>.


import serial
import re
import threading
import time

#class serialThread(threading.Thread):
#	# Override init function.
#	def __init__(self):
#		# Call super class init function.
#		super(serialThread, self).__init__()


class printer(threading.Thread):
	def __init__(self, settings, queue, queueCommands):

		# Internalise parameters.
		self.settings = settings
		self.queue = queue
		self.queueCommands = queueCommands


		# Get serial parameters from settings.
		if self.settings['printOnRaspberry'].value:
			self.port=self.settings['Port RasPi'].value
			self.baudrate=self.settings['Baud rate RasPi'].value
		else:
			self.port=self.settings['Port'].value
			self.baudrate=self.settings['Baud rate'].value


		# Stop event.
		self.stopThread = threading.Event()

		# Configure and open serial.
		try:
			self.serial = serial.Serial(
				port=self.port,
				baudrate=self.baudrate,
				bytesize = serial.EIGHTBITS, #number of bits per bytes
				parity = serial.PARITY_NONE, #set parity check: no parity
				stopbits = serial.STOPBITS_ONE,
				timeout = 0	# Wait for incoming bytes forever.
				)
			self.queue.put("Serial port " + self.settings['Port'].value + " connected.")
		# If serial port does not exist...
		except serial.SerialException:
			# ... define a dummy.
			self.serial = None
			self.queue.put("Serial port " + self.settings['Port'].value + " not found.\nMake sure your board is plugged in and you have defined the correct serial port in the settings menu.")

		# Call super class init function.
		super(printer, self).__init__()

	# Send function. This simply puts the command inside the input queue.
	# This way the send command can be initiated without having to pass a queue
	# to the serial object from outside.
	def send(self, command):
		self.queueCommands.put(command)

	# Override run function.
	# Send a command string with optional value.
	# Method allows to retry sending until ack is received as well
	# as waiting for printer to process the command.
	def run(self):
		if self.serial != None:
			self.queue.put("Serial waiting for commands to send.")
		else:
			self.queue.put('Serial not operational.')
		# Start loop.
		while 1 and not self.stopThread.isSet():
			# Get command from queue.
			if self.queueCommands.qsize():
				command = self.queueCommands.get()
				string = command[0]
				value = command[1]
				retry = command[2]
				wait = command[3]
				if self.serial != None:
					# Cast inputs.
					if value != None: value = float(value)
					if wait != None: wait = int(wait)
					# ... start infinite loop that sends and waits for ack.
					count = 0
					# Set timeout to 5 seconds.
					self.serial.timeout = 5
					while count < 5 and not self.stopThread.isSet():
						# Create command string from string and value.
						# Separate string and value by space.
						if value != None:
							string = string + " " + str(value)
						# Place send message in queue.
						self.queue.put("Sending command \"" + string + "\".")
						# Send command.
						self.serial.write(string)
						# If retry flag is set...
						if retry:
							# ... listen for ack until timeout.
							printerResponse = self.serial.readline()
							printerResponse = printerResponse.strip()
							# Compare ack with sent string. If match...
							if printerResponse == string:
								# Place success message in queue.
								self.queue.put("Command \"" + string + "\" sent successfully.")
								if wait != None:
									self.queue.put("Wait for printer to finish...")
								# ... exit the send loop.
								break
						# If retry flag is not set...
						else:
							# ... exit the loop.
							break
						# Increment counter.
						count += 1
						# Place giving up message in queue if necessary.
						if count == 5:
							self.queue.put("Printer not responding. Giving up...")

					# Wait for response from printer that signals end of action.
					# If wait value is provided...
					if wait != 0:
						# ... set timeout to one second...
						self.serial.timeout = 1
						count = 0
						while count < wait and not self.stopThread.isSet():
							# ... and listen for "done" string until timeout.
							printerResponse = self.serial.readline()
							printerResponse = printerResponse.strip()
							# Listen for "done" string.Check if return string is "done".
							if printerResponse == "done":
								self.queue.put("Printer done.")
								break
							else:
								count += 1
						# In case of timeout...
						if count == wait:
							# ... place fail message.
							self.queue.put("Printer did not finish within timeout.")
					# Reset the timeout.
					self.serial.timeout = None
					# Put done flag into queue to signal end of command process.
					self.queue.put('done')
				else:
					self.queue.put('Sending failed. Port does not exist.')
					self.queue.put('done')
			else:
				time.sleep(.1)


	# Send a command string with optional value.
	# Method allows to retry sending until ack is received as well
	# as waiting for printer to process the command.
#	def sendCommand(self, string, value=None, retry=False, wait=None):
#		self.run(string, value, retry, wait)

	def stop(self):
		self.close()
		self.queue.put("Stopping serial.")
		self.stopThread.set()

	def join(self, timeout=None):
		self.close()
		self.stopThread.set()
		threading.Thread.join(self, timeout)

	def close(self):
		if self.serial != None:
			self.serial.close()





class printerStandalone:
	def __init__(self, settings):

		# Internalise parameters.
		self.settings = settings

		self.debug = self.settings['debug'].value

		# Get serial parameters from settings.
		if self.settings['printOnRaspberry'].value:
			self.port=self.settings['portRaspi'].value
			self.baudrate=self.settings['baudrateRaspi'].value
		else:
			self.port=self.settings['port'].value
			self.baudrate=self.settings['baudrate'].value

		self.terminator = "\n"

		if not self.debug:
			print "Opening serial on port " + self.port + " at " + str(self.baudrate) + " baud."
			# Configure and open serial.
			try:
				self.serial = serial.Serial(
					port=self.port,
					baudrate=self.baudrate,
					bytesize = serial.EIGHTBITS, #number of bits per bytes
					parity = serial.PARITY_NONE, #set parity check: no parity
					stopbits = serial.STOPBITS_ONE,
					timeout = 0	# Wait for incoming bytes forever.
					)
			# If serial port does not exist...
			except serial.SerialException:
				# ... define a dummy.
				self.serial = None
				print "Could not open serial on port " + str(self.port) + " with baud rate " + str(self.baudrate) + "."
			else:
				self.flush()
		else:
			print "Serial in debug mode: not sending."
			self.serial = None

	def flush(self, timeout=1.):
		oldTimeout = self.serial.timeout
		self.serial.timeout = timeout
		string = "Flushing incoming messages."
		while string != "":
			string = self.serial.readline()
			print string
		self.serial.timeout = oldTimeout
		return string

	def waitForOk(self,timeout=.5):
		oldTimeout = self.serial.timeout
		self.serial.timeout = timeout
		for i in range(20):
			printerResponse = self.serial.readline()
			print printerResponse
			if printerResponse.strip() == "ok":
				break
			elif printerResponse.strip().split(':')[-1] == "processing":
				i = 0
				print "Processing..."
		self.serial.timeout = oldTimeout
		return printerResponse


	# Divide command in parts beginning with G or M.
	def splitGCode(self, command):
		return filter(None,re.split("([M][^MG]*|[G][^MG]*)",command))

	def sendGCode(self,command):
		commandList = self.splitGCode(command[0])
		value = command[1]
		retry = command[2]
		wait = command[3]
		for commandString in commandList:
			self.send((commandString, value, retry, wait))


	def send(self, command):
		if self.settings['debug'].value:
			pass
		else:
			# Create return value.
			returnValue = True
			# Process command.
			if len(command) < 4:
				raise ValueError('Serial command has to contain four values.')
			string = command[0]
			value = command[1]
			retry = command[2]
			wait = command[3]
			# Send command.
			if self.serial != None:
				# Cast inputs.
			#	if value != None: value = int(value)
				if wait != None: wait = int(wait)
				# Start loop that sends and waits for ack until timeout five times.
				# Set timeout to 5 seconds.
				count = 0
				self.serial.timeout = 5
				while count < 5:
					sendString = string
					# Create command string from string and value.
					# Separate string and value by space.
					if value != None:
						sendString = sendString + " " + str(value)
					print "Sending: " + sendString + "."
					# Send command.
					self.serial.write(sendString+self.terminator)
					# If retry flag is set...
					# In case fo GCode, flush input until ok is received.
					printerResponse = ""
					printerResponse = self.waitForOk()
					print "Printer response: " + printerResponse
					if retry:
						# ... listen for ack until timeout.
						printerResponse = printerResponse.strip()
						# Compare ack with sent string or with 'ok' in case of g-code board.
						# If match...
						if printerResponse == string or printerResponse == 'ok':
							# ... set the return value to success and...
							returnValue = True
							# ... exit the send loop.
						#	print "exiting"
							break
						# If ack does not match string...
						else:
							# ... set the return value to fail.
							returnValue = False
						#	print "resending"
					# If retry flag is not set...
					else:
						# ... exit the loop.
						break
					# Increment counter.
					count += 1
					# Place giving up message in queue if necessary.
				#	if count == 5:
				#		self.queue.put("Printer not responding. Giving up...")
									# Wait for response from printer that signals end of action.
				# If wait value is provided...
				if wait != None:
					# If wait value is 0...
					if wait == 0:
						#... set the timeout value to infinity.
						self.serial.timeout=0
					# Else...
					else:
						# ... set timeout to one second.
						self.serial.timeout = 1
					count = 0
					while count < wait:
						# ... and listen for "done" string until timeout.
						printerResponse = self.serial.readline()
						printerResponse = printerResponse.strip()
						# Listen for "done" string.Check if return string is "done".
						if printerResponse == "done":
							#self.queue.put("Printer done.")
							break
						else:
							count += 1
					# In case of timeout...
				#	if count == wait:
						# ... place fail message.
						#self.queue.put("Printer did not finish within timeout.")
				# Reset the timeout.
				self.serial.timeout = None
				# Flush incoming messages.
				self.flush()
				# Return success info.
				return returnValue
			else:
		#		self.flush()
				return False

	'''
	# Override run function.
	# Send a command string with optional value.
	# Method allows to retry sending until ack is received as well
	# as waiting for printer to process the command.
	def run(self):
		if self.serial != None:
			self.queue.put("Serial waiting for commands to send.")
		else:
			self.queue.put('Serial not operational.')
		# Start loop.
		while 1 and not self.stopThread.isSet():
			# Get command from queue.
			if self.queueCommands.qsize():
				command = self.queueCommands.get()
				string = command[0]
				value = command[1]
				retry = command[2]
				wait = command[3]
				if self.serial != None:
					# Cast inputs.
					if value != None: value = float(value)
					if wait != None: wait = int(wait)
					# ... start infinite loop that sends and waits for ack.
					count = 0
					# Set timeout to 5 seconds.
					self.serial.timeout = 5
					while count < 5 and not self.stopThread.isSet():
						# Create command string from string and value.
						# Separate string and value by space.
						if value != None:
							string = string + " " + str(value)
						# Place send message in queue.
						self.queue.put("Sending command \"" + string + "\".")
						# Send command.
						self.serial.write(string)
						# If retry flag is set...
						if retry:
							# ... listen for ack until timeout.
							printerResponse = self.serial.readline()
							printerResponse = printerResponse.strip()
							# Compare ack with sent string. If match...
							if printerResponse == string:
								# Place success message in queue.
								self.queue.put("Command \"" + string + "\" sent successfully.")
								if wait != None:
									self.queue.put("Wait for printer to finish...")
								# ... exit the send loop.
								break
						# If retry flag is not set...
						else:
							# ... exit the loop.
							break
						# Increment counter.
						count += 1
						# Place giving up message in queue if necessary.
						if count == 5:
							self.queue.put("Printer not responding. Giving up...")

					# Wait for response from printer that signals end of action.
					# If wait value is provided...
					if wait != 0:
						# ... set timeout to one second...
						self.serial.timeout = 1
						count = 0
						while count < wait and not self.stopThread.isSet():
							# ... and listen for "done" string until timeout.
							printerResponse = self.serial.readline()
							printerResponse = printerResponse.strip()
							# Listen for "done" string.Check if return string is "done".
							if printerResponse == "done":
								self.queue.put("Printer done.")
								break
							else:
								count += 1
						# In case of timeout...
						if count == wait:
							# ... place fail message.
							self.queue.put("Printer did not finish within timeout.")
					# Reset the timeout.
					self.serial.timeout = None
					# Put done flag into queue to signal end of command process.
					self.queue.put('done')
				else:
					self.queue.put('Sending failed. Port does not exist.')
					self.queue.put('done')
			else:
				time.sleep(.1)

	'''

	def close(self):
		if self.serial != None:
			self.serial.close()




	'''
	# Commands.
	def buildHome(self):
		self.serial.write("buildHome")
		self.waitForAckInfinite()

	def buildBaseUp(self):
		while 1:
			self.serial.timeout = 5
			self.serial.write("buildBaseUp")
			printerResponse = self.serial.readline()           # Wait for 5 sec for anything
			print "PRINTER RESPONSE: " + printerResponse
			printerResponse = printerResponse.strip()
			if printerResponse == "done":
				break
			else:
				print "      No response from printer. Resending command..."
		self.serial.timeout = None



	def buildUp(self):
		while 1:
			self.serial.write("buildUp")
			self.serial.timeout = 5
			printerResponse = self.serial.readline()           # Wait for 5 sec for anything
			print "PRINTER RESPONSE: " + printerResponse
			printerResponse = printerResponse.strip()
			if printerResponse == "done":
				break
			else:
				print "      No response from printer. Resending command..."
		self.serial.timeout = None

	def buildTop(self):
		self.serial.write("buildTop")
		self.waitForAckInfinite()

	def tilt(self):
		self.serial.write("tilt")
		self.waitForAckInfinite()

	def setStart(self):
		self.serial.write("printingFlag 1")

	def setStop(self):
		self.serial.write("printingFlag 0")

	# Settings.
	def setLayerHeight(self):
		self.serial.write("buildLayer " + str(self.settings.getLayerHeight() * self.settings.getStepsPerMm()))

	def setBaseLayerHeight(self):
		self.serial.write("buildBaseLayer " + str(self.settings.getBaseLayerHeight() * self.settings.getStepsPerMm()))

	def setBuildSpeed(self):
		self.serial.write("buildSpeed " + str(self.settings.getBuildSpeed))

	def setTiltSpeedSlow(self):
		self.serial.write("tiltSpeed " + str(self.settings.getTiltSpeedSlow))

	def setTiltSpeedFast(self):
		self.serial.write("tiltSpeed " + str(self.settings.getTiltSpeedFast))

	def setTiltAngle(self):
		self.serial.write("tiltAngle " + str(self.settings.getTiltAngle))

	def setNumberOfSlices(self, numberOfSlices):
		self.serial.write("nSlices " + str(numberOfSlices))

	def setCurrentSlice(self, currentSlice):
		self.serial.write("slice " + str(currentSlice))

#	def setTimeout(self, timeout):
#		self.serial.timeout = timeout	# Timeout for readline command. 0 is infinity, other values are seconds.

#	def waitForAckFinite(self,timeout):
#		self.serial.timeout = timeout
#		printerResponse = self.serial.readline()           # Wait for 5 sec for anything
#		print "PRINTER RESPONSE: " + printerResponse
#		printerResponse = printerResponse.strip()
#		if printerResponse=="done":
#			return 1
#		elif printerResponse != "done":
#			print "Got strange response from printer: " + printerResponse
#			return 0
#		elif printerResponse == ""
#			return 0


	def waitForAckInfinite(self):
		print "waitForAck"
		self.serial.timeout = None
		printerResponse = self.serial.readline()           # Wait forever for anything
		print "PRINTER RESPONSE: " + printerResponse
		printerResponse = printerResponse.strip()
		if printerResponse=="done":
			return "done"
		elif printerResponse != "done":
			print "Got strange response from printer: " + printerResponse
			return None
		else:
			return None


	def ping(self):
		self.serial.write("ping")
		self.serial.timeout = 10
		printerResponse = self.serial.readline()           # Wait forever for anything
		printerResponse = printerResponse.strip()
		if printerResponse!="ping":
			return 0
		else:
			return 1

	def close(self):
		if self.serial != None:
			self.serial.close()
#		print "printer serial closed"


#dontNeedThis = serialPrinter.flushInput()
	'''
class projector:

	def __init__(self, settings):

		# Internalise settings.
		self.settings = settings

		self.debug = self.settings['debug'].value

		# Configure and open serial.
		if not self.debug:
			try:
				self.serial = serial.Serial(
					port=self.settings['projectorPort'].value,
					baudrate=self.settings['projectorBaudrate'].value,
					bytesize = serial.EIGHTBITS, #number of bits per bytes
					parity = serial.PARITY_NONE, #set parity check: no parity
					stopbits = serial.STOPBITS_ONE
					)
			# If serial port does not exist...
			except serial.SerialException:
				# ... define a dummy.
				self.serial = None
		else:
			print "Projector serial in debug mode: not sending."
			self.serial = None


	def activate(self):
		command = self.settings['projectorOnCommand'].value
		if self.serial != None:
			self.serial.write(command+'\r')

	def deactivate(self):
		command = self.settings['projectorOffCommand'].value
		if self.serial != None:
			self.serial.write(command+'\r')

	def close(self):
		if self.serial != None:
			self.serial.close()
#		print "projector serial closed"
