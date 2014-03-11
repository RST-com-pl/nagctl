#!/usr/bin/env python
# coding: utf-8

# Nagios command line tool
# Copyright (C) 2010 Lesław Kopeć
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Nagios command line tool version 0.2.2

Usage: nagctl [OPTION...] COMMAND SELECTOR [PARAMETER]...

Options:
-c		path to main Nagios config file
-D		dry-run mode - do not write any commands
-h REGEXP 	match host name by REGEXP regular expression
-s REGEXP	match service name by REGEXP regular expression
-?		print help message
-v		increase verbosity

COMMANDS:
search SELECTOR
  print objects matching criteria

enable|disable SELECTOR notifications
  enable/disable notifications for matching objects

enable|disable SELECTOR checks
  enable/disable active checks for matching objects

schedule SELECTOR downtime DURATION COMMENT
  schedule downtime lasting DURATION seconds with COMMENT comment

schedule SELECTOR checks TIME
reschedule SELECTOR checks TIME
  schedule next active check in TIME seconds

acknowledge SELECTOR problems COMMENT
  acknowledge problem with object setting COMMENT comment

SELECTORS:
all
  run command on hosts and services

host
  run command on hosts only

service
  run command on services only"""


import getopt
import sys
import os

conf = {
	"cfg_dir" : [],
	"cfg_file" : [],
	"command_file" : "",
	"config" : "/etc/nagios3/nagios.cfg",
	"dry-run" : False,
	"help" : 0,
	"host" : None,
	"service" : None,
	"verbose" : 1
}

# A global list of host objects.
hosts = []
# A global list of service objects.
services = []
# A global list of hostgroup objects.
hostgroups = []

# A global dictionary of host templates.
host_tmpl = {}
# A global dictionary of service templates.
service_tmpl = {}


#########################################################################
# Classes								#
#########################################################################

class Object():
	"""A basic class that all Nagios objects are based on"""

	def __init__(self, param):
		"""Setup basic properties of a Nagios object"""

		# Upon creation no dependencies are resolved.
		self._inherited = False
		# Also parameters are not expanded to lists so
		# the object is not ready for interaction.
		self._ready = False
		self._param = param

	def splitSelector(self, list):
		"""Split a list into two include and exclude object lists"""

		include = []
		exclude = []
		if list is None:
			# A property can be unset (None) so we return None as well.
			return None
		for e in list.split(','):
			# Strip whitespace.
			e = e.strip()
			if e == "":
				continue
			if e[0] == "!":
				# Negated objects are appended to exclude list without '!' prefix.
				exclude.append(e[1:])
			else:
				include.append(e)
		return (include, exclude)

	def matchName(self, pattern):
		"""Check if host name matches a regexp pattern"""

		import re

		if self.getName() is None:
			# Object names generally should have a string value.
			# An unnamed object doesn't match in any case.
			return False
		if pattern is None:
			# Name matches when no pattern is set (match any).
			return True
		if re.search("^"+pattern+"$", self.getName()):
			return True
		else:
			return False

	def isRegistered(self):
		"""Return true if object is not template"""
		if self.getName() is None:
			return False
		if self._param.has_key("register") and self._param["register"] == 0:
			return False
		else:
			return True

	def getParam(self, key):
		"""Return object parameter by given name"""

		try:
			return self._param[key]
		except KeyError:
			return None

	def inheritParam(self, key, value):
		"""Inherit parameter value"""

		# Only inherit a parameter if the object doesn't have
		# its own one.
		if self.getParam(key) is None:
			self._param[key] = value
		elif self.getParam(key)[0] == "+":
			# Append the new value to the current parameter value.
			self._param[key] = ",".join([self._param[key], value])

	def getUses(self):
		"""Set and return a list of templates used by object"""

		try:
			return self._use
		except AttributeError:
			# Apparently the property hasn't been set yet. Let's do so.
			if "use" in self._param:
				# Set a list of used templates.
				# There are no templates preceded by exclamation mark
				# so the second parameter is discarded.
				(self._use, _) = self.splitSelector(self._param["use"])
			else:
				self._use = []
			return self._use

	def setupParams(self):
		"""Convert some essential object's parameters"""

		# Check if the object hasn't been already set up.
		if self._ready:
			return None

		# It's time to inherit parameters from parent objects.
		self.inheritTemplates()

		for key in self._param.keys():
			try:
				# Cleanup parameter value by stripping any
				# leading append marker.
				self._param[key] = self._param[key].lstrip("+")
			except AttributeError:
				# In case the parameter value is not a string (like
				# use parameter).
				pass

		self._ready = True


	def inheritTemplates(self):
		"""Inherit parameters from template objects"""

		if self._inherited:
			# This object already has all dependencies resolved
			# so its arguments can be returned now.
			return self._param

		if self.__class__.__name__ == "Host":
			tmpl = host_tmpl
		if self.__class__.__name__ == "Service":
			tmpl = service_tmpl

		# Walk through all parent objects starting from last one
		# so that the first can overwrite any arguments.
		for u in reversed(self.getUses()):
			# Check if a template exists`. 
			if u in tmpl:
				# Get all parameters from parent object after
				# its dependencies have been resolved.
				param = tmpl[u].inheritTemplates()
				# Try to inherit every parent parameter.
				for key in param.keys():
					self.inheritParam(key, param[key])

		self._inherited = True

		return self._param


class Host(Object):
	"""Class for Nagios hosts"""

	def setupParams(self):
		"""Resolve essential host parameters"""

		Object.setupParams(self)

		if "hostgroups" in self._param:
			# Convert hostgroups to a nice list.
			(self._hostgroup, _) = self.splitSelector(self._param["hostgroups"])
		else:
			self._hostgroup = []

	def getName(self):
		"""Return host name"""

		try:
			return self._param["host_name"]
		except KeyError:
			return None

	def matchService(self, include_host, exclude_host, include_group, exclude_group):
		"""Check if a service is assigned to the host"""

		matched = False
		# Check if theres an include groups are set and if the host has
		# at least one hostgroup assigned.
		if (not include_group is None) and (not self._hostgroup is None):
			for i in include_group:
				if (i in self._hostgroup) or (i == "*"):
					matched = True
		# Check if a host name is directly mentioned in include list.
		if not include_host is None:
			for i in include_host:
				if (i == self.getName()) or (i == "*"):
					matched = True
		# Check if theres an exclude groups are set and if the host has
		# at least one hostgroup assigned.
		if (not exclude_group is None) and (not self._hostgroup is None):
			for i in exclude_group:
				if i in self._hostgroup:
					matched = False
		# Check if a host name is directly mentioned in exclude list.
		if not exclude_host is None:
			for i in exclude_host:
				if i == self.getName():
					matched = False

		return matched

	def addHostgroup(self, hostgroup):
		"""Add a hostgroup to list"""

		try:
			self._hostgroup.append(hostgroup)
		except AttributeError:
			self._hostgroup = [hostgroup]


class Service(Object):
	"""Class for Nagios service objects"""

	def setupParams(self):
		"""Resolve essential host parameters"""

		Object.setupParams(self)

		if "host_name" in self._param:
			# Set two lists of hosts: included and excluded.
			(self._include_host, self._exclude_host) = self.splitSelector(self._param["host_name"])
		else:
			self._include_host = None
			self._exclude_host = None
		if "hostgroup_name" in self._param:
			# Set two lists of hostgroups: included and excluded.
			(self._include_hostgroup, self._exclude_hostgroup) = self.splitSelector(self._param["hostgroup_name"])
		else:
			self._include_hostgroup = None
			self._exclude_hostgroup = None

	def getName(self):
		"""Return service name"""

		try:
			return self._param["service_description"]
		except KeyError:
			return None

class Hostgroup(Object):
	"""Class for Nagios hostgroup objects"""

	def __init__(self, param):
		"""Setup basic properties of Nagios hostgroup object"""

		if param.has_key("hostgroup_name"):
			# Set object name.
			self._name = param["hostgroup_name"]
		else:
			self._name = None
		if param.has_key("members"):
			# Set a list of hostgroup members.
			# There are no exclude members so the second parameter is discarded.
			(self._members, _) = self.splitSelector(param["members"])
		else:
			self._members = []

	def getName(self):
		"""Return hostgroup name"""

		return self._name

	def getMembers(self):
		"""Get a list of hostgroup members"""

		return self._members


class ObjectLink():
	"""Keeps lists of object and their relationships"""

	def __init__(self):
		self._objects = []

	def getCount(self):
		"""Return the number of objects"""

		return len(self._objects)

	def addHost(self, host):
		"""Append host to list"""

		self._objects.append([host])

	def addService(self, service):
		"""Append service to list"""

		self._objects[-1].append(service)

	def getHostList(self):
		"""Return a list of all host objects"""

		return [h[0] for h in self._objects]

	def getHost(self, index):
		"""Return a host object at given index"""

		return self._objects[index][0]

	def getServiceList(self, index):
		"""Return a list of service objects at given index"""

		return self._objects[index][1:]


#########################################################################
# Functions								#
#########################################################################

def printMessage(message, verbosity = 1):
	"""Print a message if verbosity is set high enough"""

	# Decide if a message should be displayed based on verbosity levels.
	if conf["verbose"] >= verbosity:
		print message

def parseArguments():
	"""Parse command line arguments and return a dictionary
	with options"""

	# A mapping of short argument names to configuration keys.
	argmap = {
		"-?" : "help",
		"-c" : "config",
		"-D" : "dry-run",
		"-h" : "host",
		"-s" : "service",
		"-v" : "verbose"
	}

	try:
		# Resolve command line arguments.
		(opt, arg) = getopt.getopt(sys.argv[1:], "c:Dh:s:v?")

	except getopt.GetoptError, error:
		# Bail out if we can't understand command line arguments.
		sys.stderr.write("Fatal error parsing arguments: %s\n" % (str(error)))
		sys.exit(1)

	for (k, v) in opt:
		if type(conf[argmap[k]]).__name__ == 'int':
			# Increment config options that are integers.
			conf[argmap[k]] += 1
		elif type(conf[argmap[k]]).__name__ == 'bool':
			# Booleans are set to True.
			conf[argmap[k]] = True
		else:
			# Other kind of options are just set.
			conf[argmap[k]] = v

	if conf["dry-run"]:
		# Increase verbosity by one when runnig in dry-run mode.
		conf["verbose"] += 1

	return (conf, arg)

def parseConfig():
	"""Parse Nagios main configuration file"""

	# A list of options that need to be extracted from
	# main Nagios config file.
	match = ("cfg_file", "cfg_dir", "command_file")

	try:
		cfg = open(conf["config"], "r")
		printMessage("Reading "+str(conf["config"]), 3)
		try:
			for line in cfg.readlines():
				# Check if line sets a config option.
				if "=" in line:
					(k, v) = line.split("=", 1)
					# Remove leading and trailing whitespace.
					k = k.strip()
					if k in match:
						v = v.strip()
						if type(conf[k]).__name__ == "list":
							# Append value if config option is a list.
							conf[k].append(v)
						else:
							# Just set the value if config option is a string.
							conf[k] = v

		except IOError, error:
			sys.stderr.write("Cannot read main config file: %s\n" % (error))
			sys.exit(1)

		finally:
			# Make sure the file gets closed.
			cfg.close()

	except IOError, error:
		sys.stderr.write("Cannot open main config file: %s\n" % (error))
		sys.exit(1)


def searchDir(dir):
	"""Recursively search for files in a directory"""

	# Make sure that we're looking at a directory.
	if os.path.isdir(dir):
		printMessage("Searching for files in: %s" % (dir), 3)
		# Get directory contents.
		for obj in os.listdir(dir):
			path = os.path.join(dir, obj)
			# Check if path leads to a non-hidden file with .cfg extension
			if os.path.isfile(path) and (os.path.splitext(path)[1] == ".cfg") and (os.path.basename(path)[0] != "."):
				parseFile(path)
			if os.path.isdir(path):
				searchDir(path)
		
	
def parseFile(file):
	"""Parse Nagios configuration file"""

	import re

	try:
		fh = open(file, "r")
		try:
			printMessage("Reading file: %s" % (file), 3)
			# This variable keeps track of the current "define" statement
			# we're currently inside of.
			definition = None
			# A dictionary of all parameters for current object.
			param = {}

			for line in fh.readlines():
				# Remove leading and trailing whitespace.
				line = line.strip()
				if re.search("^define host\s*{$", line):
					definition = "host"
					continue
				if re.search("^define service\s*{$", line):
					definition = "service"
					continue
				if re.search("^define hostgroup\s*{$", line):
					definition = "hostgroup"
					continue
				# Check if the current definition ends here.
				if re.search("^}$", line):
					# Check if host name was set in order to skip those
					# that have none (templates).
					if (definition == "host"):
						# Create a new host object.
						h = Host(param)
						if h.isRegistered():
							# Append new object to hosts list.
							hosts.append(h)
						if not h.getParam("name") is None:
							# Add new host to host templates dictionary.
							host_tmpl[h.getParam("name")] = h

					# Check if service name was set in order to skip those
					# that have none (templates).
					if (definition == "service"):
						# Create a new service object.
						s = Service(param)
						if s.isRegistered():
							# Append new object to service list.
							services.append(s)
						if not s.getParam("name") is None:
							# Add new service to service templates dictionary.
							service_tmpl[s.getParam("name")] = s

					# Check if service name was set in order to skip those
					# that have none (templates).
					if (definition == "hostgroup") and (param.has_key("hostgroup_name")):
						# Create a new service object.
						h = Hostgroup(param)
						# Append new object to service list.
						hostgroups.append(h)
					# Reset parameters.
					param = {}
					definition = None
					continue
				# Check if we're inside an object definition.
				if not definition is None:
					# Split line by whitespace. Set keyword as first chunk
					# and value as rest.
					v = line.split(None, 1)
					if len(v) > 1:
						param[v[0]] = v[1]

		finally:
			# Make sure the file gets closed.
			fh.close()

	except IOError, error:
		sys.stderr.write("Cannot read file: %s\n" % (error))
		return None


def matchObjects():
	"""Resolve dependencies between hosts and services
	and return a nested list of matches"""

	# Create an object that will hold all other objects.
	result = ObjectLink()

	if conf["host"] is None:
		# When no host constraint was specified match all hosts.
		matched_hosts = hosts
	else:
		# Get a list of hosts filtered by name.
		matched_hosts = [h for h in hosts if h.matchName(conf["host"])]

	for h in matched_hosts:
		h.setupParams()

	# Add additional hostgroups to hosts by checking hostgroup members.
	for hostgroup in hostgroups:
		for member in hostgroup.getMembers():
			for host in matched_hosts:
				if (member == host.getName()) or (member == "*"):
					host.addHostgroup(hostgroup.getName())

	if conf["service"] is None:
		# When no service constraint was specified match all services.
		matched_services = services
	else:
		# Get a list of services filtered by name.
		matched_services = [s for s in services if s.matchName(conf["service"])]

	for s in matched_services:
		s.setupParams()

	for h in matched_hosts:
		added = False
		# Start with an empty inner list.
		for s in matched_services:
			# Check if a host have a particular service attached.
			if h.matchService(s._include_host, s._exclude_host, s._include_hostgroup, s._exclude_hostgroup):
				if not added:
					# First element of inner list is the host object.
					result.addHost(h)
					added = True
				# Append service object to inner list.
				result.addService(s)
	return result


def getSimilar(args, pack):
	"""Return a subset of objects that are similar to first argument"""

	import re

	# Make sure that args is a list or otherwise strange things might happen.
	if type(args).__name__ != "list":
		raise TypeError

	if "" in args:
		# Return empty list when first argument contains empty string.
		# This would cause regexp to always match.
		return []

	if type(pack).__name__  == "dict":
		# Return dictionary when given one as second argument.
		results = {}
		for p in pack.keys():
			count = p.count(" ") + 1
			# Limit number of elements in args to number of words in current object
			# and build a regular expression to match object key.
			if re.search("^"+"\w*\s+".join(args[:count]), p, re.IGNORECASE):
				results[p] = pack[p]

	elif type(pack).__name__  == "list":
		# Return list when given one as second argument.
		results = []
		for p in pack:
			count = p.count(" ") + 1
			# Limit number of elements in args to number of words in current object
			# and build a regular expression to match object.
			if re.search("^"+"\w*\s+".join(args[:count]), p, re.IGNORECASE):
				results.append(p)
	else:
		# Raise exception when list or dictionary not given.
		raise TypeError

	return results


def searchObjects(command, scope):
	"""Display a list o matching objects"""

	if len(command) > 1:
		sys.stderr.write("Unrecognized search parameters: %s\n" %(" ".join(command[1:])))
		sys.exit(1)

	# Resolve host and service assignments and get a filtered list of objects.
	objects = matchObjects()

	if scope == "all":
		# When no scope is defined print hosts with services.
		for i in range(0, objects.getCount()):
			print "%s: %s" % (objects.getHost(i).getName(), ", ".join([s.getName() for s in objects.getServiceList(i)]))

	if scope == "host":
		# When host scope is requested print only hosts.
		for h in objects.getHostList():
			print h.getName()

	if scope == "service":
		# When service scope is requested print only uique service names.
		services = []
		for i in range(0, objects.getCount()):
			# Get service names.
			names = [s.getName() for s in objects.getServiceList(i)]
			for n in names:
				# Filter out duplicates
				if not n in services:
					services.append(n)
		print "\n".join(services)

	# Return an empty list of commands to run.
	return []


def toggleNotifications(command, scope):
	"""Enable or disable notifications for various objects"""

	action = command[0]

	if len(command) > 2:
		sys.stderr.write("Unrecognized %s notifications parameters: %s\n" % (action, " ".join(command[2:])))
		sys.exit(1)

	if action in ["enable", "disable"]:
		# Nagios likes its commands in uppercase.
		action = action.upper()
	else:
		sys.stderr.write("Unrecognized command: %s\n" % (action))
		sys.exit(1)

	commands = []

	# Resolve host and service assignments and get a filtered list of objects.
	objects = matchObjects()

	if (scope == "host") or (scope == "all"):
		for h in objects.getHostList():
			commands.append("%s_HOST_NOTIFICATIONS;%s" % (action, h.getName()))

	if (scope == "service") or (scope == "all"):
		for i in range(0, objects.getCount()):
			# Get host object.
			h = objects.getHost(i)
			# Get service objects.
			for s in objects.getServiceList(i):
				commands.append("%s_SVC_NOTIFICATIONS;%s;%s" % (action, h.getName(), s.getName()))

	return commands


def toggleChecks(command, scope):
	"""Enable or disable active checks for various objects"""

	action = command[0]

	if len(command) > 2:
		sys.stderr.write("Unrecognized %s checks parameters: %s\n" % (action, " ".join(command[2:])))
		sys.exit(1)

	if action in ["enable", "disable"]:
		# Nagios likes its commands in uppercase.
		action = action.upper()
	else:
		sys.stderr.write("Unrecognized command: %s\n" % (action))
		return False

	commands = []

	# Resolve host and service assignments and get a filtered list of objects.
	objects = matchObjects()

	if (scope == "host") or (scope == "all"):
		for h in objects.getHostList():
			commands.append("%s_HOST_CHECK;%s" % (action, h.getName()))

	if (scope == "service") or (scope == "all"):
		for i in range(0, objects.getCount()):
			# Get host object.
			h = objects.getHost(i)
			# Get service objects.
			for s in objects.getServiceList(i):
				commands.append("%s_SVC_CHECK;%s;%s" % (action, h.getName(), s.getName()))

	return commands


def scheduleDowntime(command, scope):
	"""Schedule downtime for various objects"""

	if len(command) > 4:
		sys.stderr.write("Unrecognized schedule downtime parameters: %s\n" % (" ".join(command[2:])))
		sys.exit(1)

	if len(command) < 4:
		sys.stderr.write("Missing required command parameters: comment or duration\n")
		sys.exit(1)

	# Get duration and comment from passed parameters.
	(duration, comment) = command[-2:]
	try:
		duration = int(duration)
	except ValueError:
		# Seems that duration is not an integer.
		sys.stderr.write("Invalid parameter: %s\n" % (duration))
		sys.exit(1)

	import time

	commands = []
	timestamp = int(time.time())

	# Resolve host and service assignments and get a filtered list of objects.
	objects = matchObjects()

	if (scope == "host") or (scope == "all"):
		for h in objects.getHostList():
			commands.append("SCHEDULE_HOST_DOWNTIME;%s;%u;%u;1;0;%u;nagctl;%s" % (h.getName(), timestamp, timestamp + duration, duration, comment))

	if (scope == "service") or (scope == "all"):
		for i in range(0, objects.getCount()):
			# Get host object.
			h = objects.getHost(i)
			# Get service objects.
			for s in objects.getServiceList(i):
				commands.append("SCHEDULE_SVC_DOWNTIME;%s;%s;%u;%u;1;0;%u;nagctl;%s" % (h.getName(), s.getName(), timestamp, timestamp + duration, duration, comment))

	return commands


def scheduleCheck(command, scope):
	"""Schedule next active check for various objects"""

	if len(command) > 3:
		sys.stderr.write("Unrecognized schedule check parameters: %s\n" % (" ".join(command[2:])))
		sys.exit(1)

	if len(command) < 3:
		sys.stderr.write("Missing required command parameters: time\n")
		sys.exit(1)

	# Get duration and comment from passed parameters.
	timestamp = command[-1]
	try:
		timestamp = int(timestamp)
	except ValueError:
		# Seems that time is not an integer.
		sys.stderr.write("Invalid parameter: %s\n" % (timestamp))
		sys.exit(1)

	import time
	timestamp = int(time.time() + timestamp)

	commands = []

	# Resolve host and service assignments and get a filtered list of objects.
	objects = matchObjects()

	if (scope == "host") or (scope == "all"):
		for h in objects.getHostList():
			commands.append("SCHEDULE_HOST_CHECK;%s;%u" % (h.getName(), timestamp))

	if (scope == "service") or (scope == "all"):
		for i in range(0, objects.getCount()):
			# Get host object.
			h = objects.getHost(i)
			# Get service objects.
			for s in objects.getServiceList(i):
				commands.append("SCHEDULE_SVC_CHECK;%s;%s;%u" % (h.getName(), s.getName(), timestamp))

	return commands


def acknowledgeProblem(command, scope):
	"""Acknowledge problems for various objects"""

	if len(command) > 3:
		sys.stderr.write("Unrecognized acknowledge problems parameters: %s\n" % (" ".join(command[2:])))
		sys.exit(1)

	if len(command) < 3:
		sys.stderr.write("Missing required command parameters: comment")
		sys.exit(1)

	comment = command[-1]

	commands = []

	# Resolve host and service assignments and get a filtered list of objects.
	objects = matchObjects()

	if (scope == "host") or (scope == "all"):
		for h in objects.getHostList():
			commands.append("ACKNOWLEDGE_HOST_PROBLEM;%s;1;0;0;nagctl;%s" % (h.getName(), comment))

	if (scope == "service") or (scope == "all"):
		for i in range(0, objects.getCount()):
			# Get host object.
			h = objects.getHost(i)
			# Get service objects.
			for s in objects.getServiceList(i):
				commands.append("ACKNOWLEDGE_SVC_PROBLEM;%s;%s;1;0;0;nagctl;%s" % (h.getName(), s.getName(), comment))

	return commands


def doCommands(commands):
	"""Append given commands to Nagios external commands file"""

	if len(commands) == 0:
		# Do not bother when there are no commands to run.
		return None

	import time
	# Get current timestamp.
	timestamp = int(time.time())

	try:
		# Open Nagios external commands file for appending.
		extcmd = open(conf["command_file"], "a")
		try:
			if (conf["dry-run"]) and (conf["verbose"] > 1):
				printMessage("Dry-run mode: no commands will be written to Nagios command file\n", 0)

			for c in commands:
				printMessage("Running command: %s" % (c), 2)

				if not conf["dry-run"]:
					# Write each command to file.
					extcmd.write("[%lu] %s\n" % (timestamp, c))

		except IOError, msg:
			sys.stderr.write("Cannot write to external commands file: %s\n" % (msg))
		finally:
			# Always try to close the file no matter what.
			extcmd.close()
			if conf["dry-run"]:
				printMessage("\nDry-run mode: no commands will be written to Nagios command file", 0)
			printMessage("Written %u commands to Nagios command file" % (len(commands)), 1)

	except IOError, msg:
		sys.stderr.write("Cannot write to external commands file: %s\n" % (msg))


#########################################################################
# Main									#
#########################################################################

def main():
	# Parse command line arguments.
	(conf, arg) = parseArguments()

	if conf["help"]:
		# Display help and exit.
		print __doc__
		sys.exit(0)

	# Check if there's at least one command was passed.
	if len(arg) < 1:
		sys.stderr.write("Command not specified, terminating\n")
		print __doc__
		sys.exit(1)

	# Prepare command strings.
	if len(arg) > 1:
		selector = arg[1]
		# Remove the second list member.
		arg = [arg[0]] + arg[2:]
	else:
		selector = ""

	# A mapping of available commands to functions.
	commands = {
		"search" : searchObjects,
		"enable notifications" : toggleNotifications,
		"disable notifications" : toggleNotifications,
		"schedule downtime" : scheduleDowntime,
		"schedule checks" : scheduleCheck,
		"reschedule checks" : scheduleCheck,
		"enable checks" : toggleChecks,
		"disable checks" : toggleChecks,
		"acknowledge problems" : acknowledgeProblem
	}

	# A list of available selectors.
	selectors = [
		"host",
		"service",
		"all"
	]

	# Try to guess the correct selector.
	scope = getSimilar([selector], selectors)
	if len(scope) == 1:
		# Set scope name.
		scope = scope[0]
	elif len(scope) > 1:
		sys.stderr.write("Not sure which selector you mean:\n")
		sys.stderr.write("\n".join(scope))
		sys.exit(1)
	elif len(scope) == 0:
		sys.stderr.write("No '%s' selector found\n" % (selector))
		sys.stderr.write("Valid selectors are:\n  %s\n" % ("\n  ".join(selectors)))
		sys.exit(1)

	# Try to guess the correct command name.
	function = getSimilar(arg, commands)
	if len(function) == 1:
		# Set the full command name and function to run later.
		(names, function) = function.items()[0]
		names = names.split()
		# Replace command name with the full one.
		arg[0:len(names)] = names
	elif len(function) > 1:
		sys.stderr.write("Not sure which command you mean:\n")
		for f in function.keys():
			f = f.split()
			sys.stderr.write("  %s %s %s\n" % (f[0], scope, " ".join(f[1:])))
		sys.exit(1)
	elif len(function) == 0:
		sys.stderr.write("No '%s' command found\n" % (" ".join(arg)))
		sys.stderr.write("Valid commands are:\n  %s\n" % ("\n  ".join(commands.keys())))
		sys.exit(1)

	# Parse main Nagios configuration file.
	parseConfig()

	# Check every directory that main configuration mentions.
	for dir in conf["cfg_dir"]:
		searchDir(dir)

	# Check every file that main configuration mentions.
	for file in conf["cfg_file"]:
		parseFile(file)

	# Finally run the function that will handle the command.
	doCommands(function(arg, scope))


if __name__ == "__main__":
	main()
