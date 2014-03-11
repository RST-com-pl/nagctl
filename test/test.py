#!/usr/bin/python

"""Testing module for nagctl.py"""

import sys
import os
import unittest

# Change directory to where this module resides.
try:
	os.chdir(os.path.dirname(sys.argv[0]))
except OSError, msg:
	sys.stderr.write("Cannot change directory: "+str(msg)+"\n")
	sys.exit(1)

sys.path.append("../")
import nagctl


class Object(unittest.TestCase):
	def setUp(self):
		self.o = nagctl.Object({})
		self.h = nagctl.Host({})
		self.s = nagctl.Service({})

	def test_splitSelector_regular(self):
		"""splitSelector: divide a string into a list of strings"""

		input = "host0, host!1, !host2 , host3! ,!host4"
		include = ["host0", "host!1", "host3!"]
		exclude = ["host2", "host4"]
		self.assertEqual(self.o.splitSelector(input)[0], include)
		self.assertEqual(self.o.splitSelector(input)[1], exclude)

	def test_splitSelector_trailing(self):
		"""splitSelector: should ignore trailing comma (empty element)"""

		input = "host0, host1, "
		self.assertEqual(self.o.splitSelector(input)[0], ["host0", "host1"])

	def test_splitSelector_none(self):
		"""splitSelector: should return None when given None as argument"""

		self.assertEqual(self.o.splitSelector(None), None)

	def test_matchName_regular(self):
		"""matchName: should return True on when object name matches"""

		self.h._param["host_name"] = "host0"
		self.assertTrue(self.h.matchName("host.*"))

		self.s._param["service_description"] = "service0"
		self.assertTrue(self.s.matchName("service.*"))

	def test_matchName_match_none(self):
		"""matchName: return True when given None argument"""

		self.h._param["host_name"] = "host0"
		self.assertTrue(self.h.matchName(None))

		self.s._param["service_description"] = "service0"
		self.assertTrue(self.s.matchName(None))

	def test_matchName_host_none(self):
		"""matchName: return False when object name is None"""

		self.h._param["host_name"] = None
		self.assertFalse(self.h.matchName("pattern"))
		self.assertFalse(self.h.matchName(None))

		self.s._param["service_description"] = None
		self.assertFalse(self.s.matchName("pattern"))
		self.assertFalse(self.s.matchName(None))

	def test_isRegistered_true(self):
		"""isRegistered: return True for a complete object"""

		self.h._param["host_name"] = "Jabberwocky"
		self.assertTrue(self.h.isRegistered())

		self.h._param["register"] = 1
		self.assertTrue(self.h.isRegistered())

		self.s._param["service_description"] = "Jabberwocky"
		self.assertTrue(self.s.isRegistered())

		self.s._register = 1
		self.assertTrue(self.s.isRegistered())

	def test_isRegistered_false(self):
		"""isRegistered: return False for object template"""

		self.h._param["host_name"] = None
		self.assertFalse(self.h.isRegistered())

		self.h._param["host_name"] = "Jabberwocky"
		self.h._param["register"] = 0
		self.assertFalse(self.h.isRegistered())

		self.s._param["service_description"] = None
		self.assertFalse(self.s.isRegistered())

		self.s._param["service_description"] = "Jabberwocky"
		self.s._param["register"] = 0
		self.assertFalse(self.s.isRegistered())

	def test_getParam(self):
		"""getParam: return value of object parameter"""

		self.o._param["ping"] = "pong"
		self.assertEqual(self.o.getParam("ping"), "pong")

	def test_getParam_none(self):
		"""getParam: return None when parameter doesn't exists"""

		self.assertEqual(self.o.getParam("ping"), None)

	def test_inheritParam(self):
		"""inheritParam: set parameter value when not already set"""

		self.o.inheritParam("weight", "heavy")
		self.assertEqual(self.o.getParam("weight"), "heavy")

		self.o.inheritParam("weight", "light")
		self.assertEqual(self.o.getParam("weight"), "heavy")

	def test_inheritParam_append(self):
		"""inheritParam: append appendable parameters"""

		self.o.inheritParam("colour", "+green")
		self.o.inheritParam("colour", "yellow")
		self.assertEqual(self.o.getParam("colour"), "+green,yellow")
		self.o.inheritParam("colour", "purple")
		self.assertEqual(self.o.getParam("colour"), "+green,yellow,purple")

	def test_setupParams_defaults(self):
		"""setupParams: setup object's default paramaters"""

		self.o._param["use"] = ""
		self.o.setupParams()

		self.assertEqual(self.o._param["use"], [])
		self.assertEqual(self.o._ready, True)
		self.assertEqual(self.o._inherited, True)

	def test_setupParams(self):
		"""setupParams: setup object's common parameters"""

		# Don't bother looking for templates.
		self.o._inherited = True
		self.o._param["use"] = "guide, towel"
		self.o._param["string"] = "+appendable"
		self.o._param["trap"] = "a+bunch+of+traps+"
		self.o.setupParams()

		self.assertEqual(self.o._param["use"], ["guide", "towel"])
		self.assertEqual(self.o._param["string"], "appendable")
		self.assertEqual(self.o._param["trap"], "a+bunch+of+traps+")


class Host(unittest.TestCase):
	def setUp(self):
		self.h = nagctl.Host({"host_name":"universe", "hostgroups":"group0, group1"})

	def test_init_defaults(self):
		"""init: correctly set default host parameters"""

		self.h = nagctl.Host({})

		self.assertEqual(self.h._inherited, False)
		self.assertEqual(self.h._ready, False)
		self.assertEqual(self.h._param, {})

	def test_getName_regular(self):
		"""getName: return host's name"""

		self.h._param["host_name"] = "Spartakus"
		self.assertEqual(self.h.getName(), "Spartakus")

	def test_getName_none(self):
		"""getName: return None if name not set"""

		self.h = nagctl.Host({})
		self.assertEqual(self.h.getName(), None)

	def test_matchService_include(self):
		"""matchService: return True when a host name matches"""

		self.h.setupParams()

		self.assertTrue(self.h.matchService(["universe"], None, None, None))
		self.assertTrue(self.h.matchService(None, None, ["group1"], None))
		self.assertTrue(self.h.matchService(["*"], None, None, None))
		self.assertTrue(self.h.matchService(["universe"], ["multiverse"], None, None))
		self.assertTrue(self.h.matchService(["universe"], ["multiverse"], None, ["gibberish"]))
		self.assertTrue(self.h.matchService(None, None, ["*"], None))

	def test_matchService_exclude(self):
		"""matchService: return False when a host name doesn't match"""

		self.h.setupParams()

		self.assertFalse(self.h.matchService(None, None, None, None))
		self.assertFalse(self.h.matchService(None, None, ["group2"], None))
		self.assertFalse(self.h.matchService(["*"], None, None, ["group0"]))
		self.assertFalse(self.h.matchService(["universe"], None, None, ["group0"]))
		self.assertFalse(self.h.matchService(None, ["universe"], ["group0"], None))
		self.assertFalse(self.h.matchService(["galaxy"], None, None, None))
		self.assertFalse(self.h.matchService(["universe"], ["universe"], None, None))
		self.assertFalse(self.h.matchService(None, None, ["group0"], ["group1"]))
		self.assertFalse(self.h.matchService(None, ["universe"], ["*"], None))

	def test_addHostgroup(self):
		"""addHostgroup: append a hostgroup to host's hostgroup list"""

		self.h.setupParams()
		self.h.addHostgroup("elite")
		self.assertEqual(self.h._hostgroup, ["group0", "group1", "elite"])

	def test_setupParams_defaults(self):
		"""setupParams: setup hosts's default paramaters"""

		del self.h._param["hostgroups"]
		self.h.setupParams()

		self.assertEqual(self.h._hostgroup, [])

	def test_setupParams(self):
		"""setupParams: setup host specific parameters"""

		# Don't bother looking for templates.
		self.h._inherited = True
		self.h._param["hostgroups"] = "office, maintenaince, severs"
		self.h.setupParams()

		self.assertEqual(self.h._hostgroup, ["office", "maintenaince", "severs"])


class Service(unittest.TestCase):

	def setUp(self):
		self.s = nagctl.Service({})

	def test_init_defaults(self):
		"""init: correctly set default service parameters"""

		self.assertEqual(self.s._inherited, False)
		self.assertEqual(self.s._ready, False)
		self.assertEqual(self.s._param, {})

	def test_getName_regular(self):
		"""getName: return service's name"""

		self.s._param["service_description"] = "Nameless One"

		self.assertEqual(self.s.getName(), "Nameless One")

	def test_getName_none(self):
		"""getName: return None if service name not set"""

		self.assertEqual(self.s.getName(), None)

	def test_setupParams_defaults(self):
		"""setupParams: setup service's default paramaters"""

		self.s.setupParams()

		self.assertEqual(self.s._include_host, None)
		self.assertEqual(self.s._exclude_host, None)
		self.assertEqual(self.s._include_hostgroup, None)
		self.assertEqual(self.s._exclude_hostgroup, None)

	def test_setupParams(self):
		"""setupParams: setup service specific parameters"""

		# Don't bother looking for templates.
		self.s._inherited = True
		self.s._param["host_name"] = "omega, !mike, golf"
		self.s._param["hostgroup_name"] = "office, !maintenaince, severs"
		self.s.setupParams()

		self.assertEqual(self.s._include_host, ["omega", "golf"])
		self.assertEqual(self.s._exclude_host, ["mike"])
		self.assertEqual(self.s._include_hostgroup, ["office", "severs"])
		self.assertEqual(self.s._exclude_hostgroup, ["maintenaince"])


class Hostgroup(unittest.TestCase):

	def test_getName_regular(self):
		"""getName: return hostgroup name"""

		hostgroup = nagctl.Hostgroup({"hostgroup_name":"swarm", "members":"drone0, drone1"})

		self.assertEqual(hostgroup.getName(), "swarm")

	def test_getName_none(self):
		"""getName: return None when hostgroup name is not set"""

		hostgroup = nagctl.Hostgroup({"members":"drone0, drone1"})

		self.assertEqual(hostgroup.getName(), None)

	def test_getMembers_regular(self):
		"""getName: return a list of host names"""

		hostgroup = nagctl.Hostgroup({"hostgroup_name":"swarm", "members":"drone0, drone1"})

		self.assertEqual(hostgroup.getMembers(), ["drone0", "drone1"])

	def test_getMembers_none(self):
		"""getName: return empty list when members are not set"""

		hostgroup = nagctl.Hostgroup({"hostgroup_name":"swarm"})

		self.assertEqual(hostgroup.getMembers(), [])


class ObjectLink(unittest.TestCase):
	def setUp(self):
		self.objects = nagctl.ObjectLink()

	def test_addHost(self):
		"""addHost: append host objects to internal list"""

		h0 = nagctl.Host({})
		self.objects.addHost(h0)

		self.assertEqual(self.objects.getHostList(), [h0])

		h1 = nagctl.Host({})
		self.objects.addHost(h1)

		self.assertEqual(self.objects.getHostList(), [h0, h1])

	def test_addService(self):
		"""addService: append service objects to internal list"""

		h0 = nagctl.Host({})
		self.objects.addHost(h0)

		self.assertEqual(self.objects.getServiceList(0), [])

		s0 = nagctl.Service({})
		self.objects.addService(s0)

		self.assertEqual(self.objects.getServiceList(0), [s0])

		s1 = nagctl.Service({})
		self.objects.addService(s1)

		self.assertEqual(self.objects.getServiceList(0), [s0, s1])


	def test_addService_none(self):
		"""addService: raise IndexError when adding service to non-existent host"""

		s0 = nagctl.Service({})
		self.assertRaises(IndexError, self.objects.addService, s0)


	def test_getHost(self):
		"""getHost: return a host object"""

		h0 = nagctl.Host({})
		self.objects.addHost(h0)

		self.assertEqual(self.objects.getHost(0), h0)

		h1 = nagctl.Host({})
		self.objects.addHost(h1)

		self.assertEqual(self.objects.getHost(0), h0)
		self.assertEqual(self.objects.getHost(1), h1)


	def test_getHost_exception(self):
		"""getHost: raise IndexError when getting non-existent host"""

		self.assertRaises(IndexError, self.objects.getHost, 0)


	def test_getServiceList(self):
		"""getServiceList: return a list of service objects"""

		h0 = nagctl.Host({})
		self.objects.addHost(h0)

		self.assertEqual(self.objects.getServiceList(0), [])

		s0 = nagctl.Service({})
		self.objects.addService(s0)

		self.assertEqual(self.objects.getServiceList(0), [s0])

		s1 = nagctl.Service({})
		self.objects.addService(s1)

		self.assertEqual(self.objects.getServiceList(0), [s0, s1])


	def test_getServiceList_exception(self):
		"""getServiceList: raise IndexError when getting non-existent service list"""

		self.assertRaises(IndexError, self.objects.getServiceList, 0)


class Main_parseArgument(unittest.TestCase):
	def setUp(self):
		nagctl.conf["dry-run"] = 0
		nagctl.conf["help"] = 0
		nagctl.conf["verbose"] = 1

	def test_parseArgument_option(self):
		"""parseArguments: set a string option"""

		nagctl.conf["config"] = "default.cfg"
		sys.argv = ["test.py", "-c", "test.cfg"]
		self.assertEqual(nagctl.parseArguments()[0]["config"], "test.cfg")

	def test_parseArgument_command(self):
		"""parseArguments: set commands"""

		sys.argv = ["test.py", "-?", "command", "and", "conquer"]
		self.assertEqual(nagctl.parseArguments()[1][:], ["command", "and", "conquer"])

	def test_parseArgument_increment(self):
		"""parseArguments: increment a numeric option"""

		sys.argv = ["test.py", "-?", "-v", "-?"]
		self.assertEqual(nagctl.parseArguments()[0]["help"], 2)
		nagctl.conf["verbose"] = 1
		self.assertEqual(nagctl.parseArguments()[0]["verbose"], 2)

	def test_parseArgument_dry_run_verbose(self):
		"""parseArguments: dry-run mode should increase verbosity"""

		sys.argv = ["test.py", "-D"]
		self.assertEqual(nagctl.parseArguments()[0]["verbose"], 2)

	def test_parseArgument_bogus(self):
		"""parseArguments: exit on unknown option"""

		sys.argv = ["test.py", "-Z"]
		self.assertRaises(SystemExit, nagctl.parseArguments)


class Main(unittest.TestCase):
	def setUp(self):
		nagctl.conf["cfg_file"] = []
		nagctl.conf["cfg_dir"] = []
		nagctl.hosts = []
		nagctl.services = []

	def test_parseConfig_missing(self):
		"""parseConfig: exit when file does not exists"""

		nagctl.conf["config"] = "notexisting.cfg"
		self.assertRaises(SystemExit, nagctl.parseConfig)

	def test_parseConfig_regular(self):
		"""parseConfig: read values from file into main config dictionary"""

		nagctl.conf["config"] = "main.cfg"
		nagctl.parseConfig()
		self.assertEquals(nagctl.conf["cfg_file"], ["hosts.cfg", "services.cfg", "hostgroups.cfg"])
		self.assertEquals(nagctl.conf["cfg_dir"], ["conf.d"])

	def test_parseFile_missing(self):
		"""parseFile: return None when not able to read file"""

		self.assertEqual(nagctl.parseFile("nonexisting.cfg"), None)

	def test_parseFile_host(self):
		"""parseFile: extract host definitions from file"""

		nagctl.parseFile("hosts.cfg")
		names = [host.getName() for host in nagctl.hosts]
		groups = [host.getParam("hostgroups") for host in nagctl.hosts]
		self.assertEqual(names, ["database0", "database1", "firewall external", "worker0"])
		self.assertEqual(groups, ['databases', 'databases, backup', 'network', None])

	def test_parseFile_service(self):
		"""parseFile: extract service definitions from file"""

		nagctl.parseFile("services.cfg")
		names = [service.getName() for service in nagctl.services]
		host = [service.getParam("host_name") for service in nagctl.services]
		hostgroup = [service.getParam("hostgroup_name") for service in nagctl.services]
		self.assertEqual(names, ["disk space", "CPU", "transaction", "SMTP"])
		self.assertEqual(host, [None, "firewall0", None, "!firewall0"])
		self.assertEqual(hostgroup, ["databases", "databases, backup", "!workers, !network, databases", "databases, workers"])

	def test_parseFile_host_template(self):
		"""parseFile: extract host template definitions from file"""

		nagctl.parseFile("templates.cfg")
		names = [host.getName() for host in nagctl.host_tmpl.values()]
		names.sort()
		self.assertEqual(names, ["generic-host", "generic-worker"])

	def test_parseFile_service_template(self):
		"""parseFile: extract service template definitions from file"""

		nagctl.parseFile("templates.cfg")
		names = [service.getName() for service in nagctl.service_tmpl.values()]
		names.sort()
		self.assertEqual(names, ["generic-cpu", "generic-service"])

	def test_searchDir_missing(self):
		"""searchDir: set no objects when directory doesn't exists"""

		nagctl.searchDir("nonexisting.d")
		hosts = [host.getName() for host in nagctl.hosts]
		services = [service.getName() for service in nagctl.services]
		self.assertEqual(hosts, [])
		self.assertEqual(services, [])

	def test_searchDir_regular(self):
		"""searchDir: set host and service objects read from all files"""

		nagctl.searchDir("conf.d")
		hosts = [host.getName() for host in nagctl.hosts]
		hosts.sort()
		services = [service.getName() for service in nagctl.services]
		services.sort()
		self.assertEqual(hosts, ["multiverse", "universe"])
		self.assertEqual(services, ["ping"])


class Main_getSimilar(unittest.TestCase):
	def setUp(self):
		self.commands = {
			"enable host" : 0,
			"enchant host" : 1,
			"hug" : 2
		}

		self.selectors = [
			"host",
			"hosts",
			"almost everything",
			"almost honest"
		]

	def test_getSimilar_list(self):
		"""getSimilar: return a list of one match"""

		self.assertEqual(nagctl.getSimilar(["hosts"], self.selectors), ["hosts"])
		self.assertEqual(nagctl.getSimilar(["HOSTS"], self.selectors), ["hosts"])
		self.assertEqual(nagctl.getSimilar(["a", "ever"], self.selectors), ["almost everything"])
		self.assertEqual(nagctl.getSimilar(["hosts", "monkeys"], self.selectors), ["hosts"])

	def test_getSimilar_list_more(self):
		"""getSimilar: return a list of multiple matches"""

		self.assertEqual(nagctl.getSimilar(["host"], self.selectors), ["host", "hosts"])
		self.assertEqual(nagctl.getSimilar(["HOST"], self.selectors), ["host", "hosts"])
		self.assertEqual(nagctl.getSimilar(["almost"], self.selectors), ["almost everything", "almost honest"])

	def test_getSimilar_list_empty(self):
		"""getSimilar: return an empty list without any matches"""

		self.assertEqual(nagctl.getSimilar(["service"], self.selectors), [])
		self.assertEqual(nagctl.getSimilar(["aho"], self.selectors), [])

	def test_getSimilar_dict(self):
		"""getSimilar: return a dictionary of one match"""

		self.assertEqual(nagctl.getSimilar(["enab", "ho"], self.commands), {"enable host":0})
		self.assertEqual(nagctl.getSimilar(["ENAB", "HO"], self.commands), {"enable host":0})
		self.assertEqual(nagctl.getSimilar(["enab", "ho", "pretty", "please"], self.commands), {"enable host":0})
		self.assertEqual(nagctl.getSimilar(["hug"], self.commands), {"hug":2})

	def test_getSimilar_dict_more(self):
		"""getSimilar: return a dictionary of multiple matches"""

		self.assertEqual(nagctl.getSimilar(["en", "h"], self.commands), {"enable host":0, "enchant host":1})
		self.assertEqual(nagctl.getSimilar(["EN", "H"], self.commands), {"enable host":0, "enchant host":1})
		self.assertEqual(nagctl.getSimilar(["en"], self.commands), {"enable host":0, "enchant host":1})

	def test_getSimilar_dict_empty(self):
		"""getSimilar: return an empty dictionary without any matches"""

		self.assertEqual(nagctl.getSimilar(["energize", "me"], self.commands), {})
		self.assertEqual(nagctl.getSimilar(["xen", "host"], self.commands), {})

	def test_getSimilar_none(self):
		"""getSimilar: return empty list when first argument is an empty string"""

		self.assertEqual(nagctl.getSimilar([""], self.commands), [])

	def test_getSimilar_exception_first(self):
		"""getSimilar: raise TypeError when first argument is not a list"""

		self.assertRaises(TypeError, nagctl.getSimilar, "a string", [])
		self.assertRaises(TypeError, nagctl.getSimilar, "a string", {})

	def test_getSimilar_exception_second(self):
		"""getSimilar: raise TypeError when second argument is not a list or dictionary"""

		self.assertRaises(TypeError, nagctl.getSimilar, [], None)


class Main_matchObjects(unittest.TestCase):
	def setUp(self):
		nagctl.conf["host"] = None
		nagctl.conf["service"] = None
		nagctl.hosts = []
		nagctl.services = []
		nagctl.hosts.append(nagctl.Host({"host_name":"worker0", "hostgroups":"group0"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"worker1", "hostgroups":"group1"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"database", "hostgroups":"group0, group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue0", "hostgroup_name":"group0"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue1", "hostgroup_name":"group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"load", "hostgroup_name":"group0, group1"}))

	def test_matchObjects_all(self):
		"""matchObjects: return all hosts and services"""

		objects = nagctl.matchObjects()
		self.assertEqual(objects.getHostList(), nagctl.hosts)

		expected = [["queue0", "load"], ["queue1", "load"], ["queue0", "queue1", "load"]]
		services = []
		for i in range(0, objects.getCount()):
			services.append([s.getName() for s in objects.getServiceList(i)])
		self.assertEqual(services, expected)

	def test_matchObjects_host(self):
		"""matchObjects: return a list of hosts and services filtered by host"""

		nagctl.conf["host"] = "worker[0-9]"

		objects = nagctl.matchObjects()
		hosts = [h.getName() for h in objects.getHostList()]
		self.assertEqual(hosts, ["worker0", "worker1"])

		services = []
		expected = [["queue0", "load"], ["queue1", "load"]]
		for i in range(0, objects.getCount()):
			services.append([s.getName() for s in objects.getServiceList(i)])
		self.assertEqual(services, expected)

	def test_matchObjects_service(self):
		"""matchObjects: return a list of hosts and services filtered by service"""

		nagctl.conf["service"] = "load"

		objects = nagctl.matchObjects()
		hosts = [h.getName() for h in objects.getHostList()]
		self.assertEqual(hosts, ["worker0", "worker1", "database"])

		expected = [["load"], ["load"], ["load"]]
		services = []
		for i in range(0, objects.getCount()):
			services.append([s.getName() for s in objects.getServiceList(i)])
		self.assertEqual(services, expected)

	def test_matchObjects_none(self):
		"""matchObjects: return empty list when no object matches"""

		nagctl.conf["host"] = "dummy"

		objects = nagctl.matchObjects()
		hosts = objects.getHostList()
		self.assertEqual(hosts, [])

		nagctl.conf["host"] = None
		nagctl.conf["service"] = "dummy"

		services = []
		objects = nagctl.matchObjects()
		for i in range(0, objects.getCount()):
			services.append(objects.getServiceList(i))
		self.assertEqual(services, [])


class Main_toggleNotifications(unittest.TestCase):
	def setUp(self):
		nagctl.conf["host"] = None
		nagctl.conf["service"] = None
		nagctl.hosts = []
		nagctl.services = []
		nagctl.hosts.append(nagctl.Host({"host_name":"worker0", "hostgroups":"group0"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"worker1", "hostgroups":"group1"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"database", "hostgroups":"group0, group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue0", "hostgroup_name":"group0"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue1", "hostgroup_name":"group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"load", "hostgroup_name":"group0, group1"}))

	def test_toggleNotifications_enable_host(self):
		"""toggleNotifications: generate commands to enable host notifications"""

		nagctl.conf["host"] = "database"
		commands = nagctl.toggleNotifications(["enable", "notifications"], "host")

		expected = ["ENABLE_HOST_NOTIFICATIONS;database"]
		self.assertEqual(commands, expected)

	def test_toggleNotifications_disable_host(self):
		"""toggleNotifications: generate commands to disable host notifications"""

		nagctl.conf["host"] = "worker[01]"
		commands = nagctl.toggleNotifications(["disable", "notifications"], "host")

		expected = ["DISABLE_HOST_NOTIFICATIONS;worker0", "DISABLE_HOST_NOTIFICATIONS;worker1"]
		self.assertEqual(commands, expected)

	def test_toggleNotifications_enable_service(self):
		"""toggleNotifications: generate commands to enable service notifications"""

		nagctl.conf["service"] = "load"
		commands = nagctl.toggleNotifications(["enable", "notifications"], "service")

		expected = ["ENABLE_SVC_NOTIFICATIONS;worker0;load", "ENABLE_SVC_NOTIFICATIONS;worker1;load", "ENABLE_SVC_NOTIFICATIONS;database;load"]
		self.assertEqual(commands, expected)

	def test_toggleNotifications_disable_service(self):
		"""toggleNotifications: generate commands to disable service notifications"""

		nagctl.conf["service"] = "queue0"
		commands = nagctl.toggleNotifications(["disable", "notifications"], "service")

		expected = ["DISABLE_SVC_NOTIFICATIONS;worker0;queue0", "DISABLE_SVC_NOTIFICATIONS;database;queue0"]
		self.assertEqual(commands, expected)

	def test_toggleNotifications_enable_all(self):
		"""toggleNotifications: generate commands to enable host and service notifications"""

		nagctl.conf["host"] = "database"
		nagctl.conf["service"] = "load"
		commands = nagctl.toggleNotifications(["enable", "notifications"], "all")

		expected = ["ENABLE_HOST_NOTIFICATIONS;database", "ENABLE_SVC_NOTIFICATIONS;database;load"]
		self.assertEqual(commands, expected)

	def test_toggleNotifications_disable_all(self):
		"""toggleNotifications: generate commands to disable host and service notifications"""

		nagctl.conf["host"] = "worker1"
		nagctl.conf["service"] = "queue1"
		commands = nagctl.toggleNotifications(["disable", "notifications"], "all")

		expected = ["DISABLE_HOST_NOTIFICATIONS;worker1", "DISABLE_SVC_NOTIFICATIONS;worker1;queue1"]
		self.assertEqual(commands, expected)

	def test_toggleNotifications_none(self):
		"""toggleNotifications: do not generate any commands"""

		nagctl.conf["host"] = "worker0"
		nagctl.conf["service"] = "queue1"
		commands = nagctl.toggleNotifications(["disable", "notifications"], "all")

		expected = []
		self.assertEqual(commands, expected)

	def test_toggleNotifications_invalid_argument_count(self):
		"""toggleNotifications: exit when argument count is invalid"""

		self.assertRaises(SystemExit, nagctl.toggleNotifications, ["disable", "notifications", "invalid"], "all")

	def test_toggleNotifications_invalid_action(self):
		"""toggleNotifications: exit when action is unrecognized"""

		self.assertRaises(SystemExit, nagctl.toggleNotifications, ["invalid", "notifications"], "all")


class Main_toggleChecks(unittest.TestCase):
	def setUp(self):
		nagctl.conf["host"] = None
		nagctl.conf["service"] = None
		nagctl.hosts = []
		nagctl.services = []
		nagctl.hosts.append(nagctl.Host({"host_name":"worker0", "hostgroups":"group0"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"worker1", "hostgroups":"group1"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"database", "hostgroups":"group0, group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue0", "hostgroup_name":"group0"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue1", "hostgroup_name":"group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"load", "hostgroup_name":"group0, group1"}))

	def test_toggleChecks_enable_host(self):
		"""toggleChecks: generate commands to enable host checks"""

		nagctl.conf["host"] = "database"
		commands = nagctl.toggleChecks(["enable", "checks"], "host")

		expected = ["ENABLE_HOST_CHECK;database"]
		self.assertEqual(commands, expected)

	def test_toggleChecks_disable_host(self):
		"""toggleChecks: generate commands to disable host checks"""

		nagctl.conf["host"] = "worker[01]"
		commands = nagctl.toggleChecks(["disable", "checks"], "host")

		expected = ["DISABLE_HOST_CHECK;worker0", "DISABLE_HOST_CHECK;worker1"]
		self.assertEqual(commands, expected)

	def test_toggleChecks_enable_service(self):
		"""toggleChecks: generate commands to enable service checks"""

		nagctl.conf["service"] = "load"
		commands = nagctl.toggleChecks(["enable", "checks"], "service")

		expected = ["ENABLE_SVC_CHECK;worker0;load", "ENABLE_SVC_CHECK;worker1;load", "ENABLE_SVC_CHECK;database;load"]
		self.assertEqual(commands, expected)

	def test_toggleChecks_disable_service(self):
		"""toggleChecks: generate commands to disable service checks"""

		nagctl.conf["service"] = "queue0"
		commands = nagctl.toggleChecks(["disable", "checks"], "service")

		expected = ["DISABLE_SVC_CHECK;worker0;queue0", "DISABLE_SVC_CHECK;database;queue0"]
		self.assertEqual(commands, expected)

	def test_toggleChecks_enable_all(self):
		"""toggleChecks: generate commands to enable host and service checks"""

		nagctl.conf["host"] = "database"
		nagctl.conf["service"] = "load"
		commands = nagctl.toggleChecks(["enable", "checks"], "all")

		expected = ["ENABLE_HOST_CHECK;database", "ENABLE_SVC_CHECK;database;load"]
		self.assertEqual(commands, expected)

	def test_toggleChecks_disable_all(self):
		"""toggleChecks: generate commands to disable host and service checks"""

		nagctl.conf["host"] = "worker1"
		nagctl.conf["service"] = "queue1"
		commands = nagctl.toggleChecks(["disable", "checks"], "all")

		expected = ["DISABLE_HOST_CHECK;worker1", "DISABLE_SVC_CHECK;worker1;queue1"]
		self.assertEqual(commands, expected)

	def test_toggleChecks_none(self):
		"""toggleChecks: do not generate any commands"""

		nagctl.conf["host"] = "worker0"
		nagctl.conf["service"] = "queue1"
		commands = nagctl.toggleChecks(["disable", "checks"], "all")

		expected = []
		self.assertEqual(commands, expected)

	def test_toggleChecks_invalid_argument_count(self):
		"""toggleChecks: exit when argument count is invalid"""

		self.assertRaises(SystemExit, nagctl.toggleChecks, ["disable", "checks", "invalid"], "all")


class Main_scheduleDowntime(unittest.TestCase):
	def setUp(self):
		nagctl.conf["host"] = None
		nagctl.conf["service"] = None
		nagctl.hosts = []
		nagctl.services = []
		nagctl.hosts.append(nagctl.Host({"host_name":"worker0", "hostgroups":"group0"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"worker1", "hostgroups":"group1"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"database", "hostgroups":"group0, group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue0", "hostgroup_name":"group0"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue1", "hostgroup_name":"group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"load", "hostgroup_name":"group0, group1"}))

	def test_scheduleDowntime_host(self):
		"""scheduleDowntime: generate commands to schedule host downtime"""

		nagctl.conf["host"] = "database"
		commands = nagctl.scheduleDowntime(["schedule", "downtime", "3600", "comment"], "host")
		for i in range (0, len(commands)):
			commands[i] = commands[i].split(";")
			# Check if timestamps set proper duration.
			self.assertEqual(int(commands[i][-6]) - int(commands[i][-7]), 3600)
			# Remove timestamps from command list before comparing commands.
			commands[i] = commands[i][:-7] + commands[i][-5:]

		expected = [["SCHEDULE_HOST_DOWNTIME", "database", "1", "0", "3600", "nagctl", "comment"]]
		self.assertEqual(commands, expected)

	def test_scheduleDowntime_service(self):
		"""scheduleDowntime: generate commands to schedule service downtime"""

		nagctl.conf["service"] = "load"
		commands = nagctl.scheduleDowntime(["schedule", "downtime", "3600", "comment"], "service")
		for i in range (0, len(commands)):
			commands[i] = commands[i].split(";")
			# Check if timestamps set proper duration.
			self.assertEqual(int(commands[i][-6]) - int(commands[i][-7]), 3600)
			# Remove timestamps from command list before comparing commands.
			commands[i] = commands[i][:-7] + commands[i][-5:]

		expected = [["SCHEDULE_SVC_DOWNTIME", "worker0", "load", "1", "0", "3600", "nagctl", "comment"], ["SCHEDULE_SVC_DOWNTIME", "worker1", "load", "1", "0", "3600", "nagctl", "comment"], ["SCHEDULE_SVC_DOWNTIME", "database", "load", "1", "0", "3600", "nagctl", "comment"]]
		self.assertEqual(commands, expected)

	def test_scheduleDowntime_all(self):
		"""scheduleDowntime: generate commands to schedule host and service downtime"""

		nagctl.conf["host"] = "database"
		nagctl.conf["service"] = "load"
		commands = nagctl.scheduleDowntime(["schedule", "downtime", "3600", "comment"], "all")
		for i in range (0, len(commands)):
			commands[i] = commands[i].split(";")
			# Check if timestamps set proper duration.
			self.assertEqual(int(commands[i][-6]) - int(commands[i][-7]), 3600)
			# Remove timestamps from command list before comparing commands.
			commands[i] = commands[i][:-7] + commands[i][-5:]

		expected = [["SCHEDULE_HOST_DOWNTIME", "database", "1", "0", "3600", "nagctl", "comment"], ["SCHEDULE_SVC_DOWNTIME", "database", "load", "1", "0", "3600", "nagctl", "comment"]]
		self.assertEqual(commands, expected)

	def test_scheduleDowntime_none(self):
		"""scheduleDowntime: do not generate any commands"""

		nagctl.conf["host"] = "worker0"
		nagctl.conf["service"] = "queue1"
		commands = nagctl.scheduleDowntime(["schedule", "downtime", "3600", "comment"], "all")

		expected = []
		self.assertEqual(commands, expected)

	def test_scheduleDowntime_invalid_argument_count(self):
		"""scheduleDowntime: exit when argument count is invalid"""

		self.assertRaises(SystemExit, nagctl.scheduleDowntime, ["schedule", "downtime", "3600", "comment", "invalid"], "all")
		self.assertRaises(SystemExit, nagctl.scheduleDowntime, ["schedule", "downtime", "3600"], "all")
		self.assertRaises(SystemExit, nagctl.scheduleDowntime, ["schedule", "downtime"], "all")

	def test_scheduleDowntime_invalid_duration(self):
		"""scheduleDowntime: exit when duration is invalid"""

		self.assertRaises(SystemExit, nagctl.scheduleDowntime, ["schedule", "downtime", "invalid", "comment"], "all")


class Main_scheduleCheck(unittest.TestCase):
	def setUp(self):
		nagctl.conf["host"] = None
		nagctl.conf["service"] = None
		nagctl.hosts = []
		nagctl.services = []
		nagctl.hosts.append(nagctl.Host({"host_name":"worker0", "hostgroups":"group0"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"worker1", "hostgroups":"group1"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"database", "hostgroups":"group0, group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue0", "hostgroup_name":"group0"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue1", "hostgroup_name":"group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"load", "hostgroup_name":"group0, group1"}))

	def test_scheduleCheck_host(self):
		"""scheduleCheck: generate commands to schedule host check"""

		import re

		nagctl.conf["host"] = "database"
		commands = nagctl.scheduleCheck(["schedule", "check", "3600"], "host")
		for i in range (0, len(commands)):
			commands[i] = commands[i].split(";")
			# Check if timestamp is an integer.
			self.assertTrue(re.match("^\d+$", commands[i][-1]))
			# Remove timestamp from command list before comparing commands.
			commands[i] = commands[i][:-1]

		expected = [["SCHEDULE_HOST_CHECK", "database"]]
		self.assertEqual(commands, expected)

	def test_scheduleCheck_service(self):
		"""scheduleCheck: generate commands to schedule service check"""

		import re

		nagctl.conf["service"] = "load"
		commands = nagctl.scheduleCheck(["schedule", "check", "3600"], "service")
		for i in range (0, len(commands)):
			commands[i] = commands[i].split(";")
			# Check if timestamp is an integer.
			self.assertTrue(re.match("^\d+$", commands[i][-1]))
			# Remove timestamp from command list before comparing commands.
			commands[i] = commands[i][:-1]

		expected = [["SCHEDULE_SVC_CHECK", "worker0", "load"], ["SCHEDULE_SVC_CHECK", "worker1", "load"], ["SCHEDULE_SVC_CHECK", "database", "load"]]
		self.assertEqual(commands, expected)

	def test_scheduleCheck_all(self):
		"""scheduleCheck: generate commands to schedule host and service check"""

		import re

		nagctl.conf["host"] = "database"
		nagctl.conf["service"] = "load"
		commands = nagctl.scheduleCheck(["schedule", "check", "3600"], "all")
		for i in range (0, len(commands)):
			commands[i] = commands[i].split(";")
			# Check if timestamp is an integer.
			self.assertTrue(re.match("^\d+$", commands[i][-1]))
			# Remove timestamp from command list before comparing commands.
			commands[i] = commands[i][:-1]

		expected = [["SCHEDULE_HOST_CHECK", "database"], ["SCHEDULE_SVC_CHECK", "database", "load"]]
		self.assertEqual(commands, expected)

	def test_scheduleCheck_none(self):
		"""scheduleCheck: do not generate any commands"""

		nagctl.conf["host"] = "worker0"
		nagctl.conf["service"] = "queue1"
		commands = nagctl.scheduleCheck(["schedule", "check", "3600"], "all")

		expected = []
		self.assertEqual(commands, expected)

	def test_scheduleCheck_invalid_argument_count(self):
		"""scheduleCheck: exit when argument count is invalid"""

		self.assertRaises(SystemExit, nagctl.scheduleCheck, ["schedule", "check", "3600", "invalid"], "all")
		self.assertRaises(SystemExit, nagctl.scheduleCheck, ["schedule", "check"], "all")

	def test_scheduleCheck_invalid_duration(self):
		"""scheduleCheck: exit when duration is invalid"""

		self.assertRaises(SystemExit, nagctl.scheduleCheck, ["schedule", "check", "invalid"], "all")


class Main_acknowledgeProblem(unittest.TestCase):
	def setUp(self):
		nagctl.conf["host"] = None
		nagctl.conf["service"] = None
		nagctl.hosts = []
		nagctl.services = []
		nagctl.hosts.append(nagctl.Host({"host_name":"worker0", "hostgroups":"group0"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"worker1", "hostgroups":"group1"}))
		nagctl.hosts.append(nagctl.Host({"host_name":"database", "hostgroups":"group0, group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue0", "hostgroup_name":"group0"}))
		nagctl.services.append(nagctl.Service({"service_description":"queue1", "hostgroup_name":"group1"}))
		nagctl.services.append(nagctl.Service({"service_description":"load", "hostgroup_name":"group0, group1"}))

	def test_acknowledgeProblem_host(self):
		"""acknowledgeProblem: generate commands to acknowledge host problem"""

		nagctl.conf["host"] = "database"
		commands = nagctl.acknowledgeProblem(["acknowledge", "problem", "comment"], "host")

		expected = ["ACKNOWLEDGE_HOST_PROBLEM;database;1;0;0;nagctl;comment"]
		self.assertEqual(commands, expected)

	def test_acknowledgeProblem_service(self):
		"""acknowledgeProblem: generate commands to acknowledge service problem"""

		import re

		nagctl.conf["service"] = "load"
		commands = nagctl.acknowledgeProblem(["acknowledge", "problem", "comment"], "service")

		expected = ["ACKNOWLEDGE_SVC_PROBLEM;worker0;load;1;0;0;nagctl;comment", "ACKNOWLEDGE_SVC_PROBLEM;worker1;load;1;0;0;nagctl;comment", "ACKNOWLEDGE_SVC_PROBLEM;database;load;1;0;0;nagctl;comment"]
		self.assertEqual(commands, expected)

	def test_acknowledgeProblem_all(self):
		"""acknowledgeProblem: generate commands to acknowledge host and service problem"""

		import re

		nagctl.conf["host"] = "database"
		nagctl.conf["service"] = "load"
		commands = nagctl.acknowledgeProblem(["acknowledge", "problem", "comment"], "all")

		expected = ["ACKNOWLEDGE_HOST_PROBLEM;database;1;0;0;nagctl;comment", "ACKNOWLEDGE_SVC_PROBLEM;database;load;1;0;0;nagctl;comment"]
		self.assertEqual(commands, expected)

	def test_acknowledgeProblem_none(self):
		"""acknowledgeProblem: do not generate any commands"""

		nagctl.conf["host"] = "worker0"
		nagctl.conf["service"] = "queue1"
		commands = nagctl.acknowledgeProblem(["acknowledge", "problem", "comment"], "all")

		expected = []
		self.assertEqual(commands, expected)

	def test_acknowledgeProblem_invalid_argument_count(self):
		"""acknowledgeProblem: exit when argument count is invalid"""

		self.assertRaises(SystemExit, nagctl.acknowledgeProblem, ["schedule", "check", "comment", "invalid"], "all")
		self.assertRaises(SystemExit, nagctl.acknowledgeProblem, ["schedule", "check"], "all")


if __name__ == "__main__":
	unittest.main()
