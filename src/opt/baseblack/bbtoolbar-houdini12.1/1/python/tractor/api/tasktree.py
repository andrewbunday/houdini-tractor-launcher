import time		
import getpass
import re

from tractor.ordereddict import OrderedDict

class TaskTree( object ):
	"""Base class for tractor based job scripts. This class should not be called directly."""
	# tasks are stored within a dict within each Task. There is therefore no global 
	# list of all of the nodes in the tree. It would be possible to overload the OrderedDict
	# to create a global name variable to keep track of all insertions from any instance 
	# of the ODict.
	
	def __init__(self):
		pass
	
	def __getattr__( self, attr ):
		try:	
			return self.tasks.__getitem__( attr )
		except KeyError, inst:
			#print "Warning: %s is not a known task id or methodname" % inst
			raise AttributeError
		
	def addTask( self, task ):
		"""A task can be created outside of the job tree and added afterwards or
		it can be created by passing a valid name"""
		
		# Since either a simple string or a Task object may have been provided
		# as an argument the returned task is indexed in the task dictionary by 
		# a key whose setting is dependant on the type of the argument.
				
		if isinstance( task, Task ):
			# Check to see if another task already exists within the job tree
			# with the same name, referenced as task.name. To do this we 
			# match against the list of keys looking for matching names less
			# the "_NodeNNN" that is added. A list of matches is returned 
			# of which we only want the last one. 
			
			# This method is fairly obviously fraught with peril once/if a task 
			# graph becomes too large. If performance becomes too bad then 
			# it may be easier to switch to the simpler, if two nodes are named 
			# the same then they second will be preservered, overwriting the 
			# first.
			
			## Simple Version
			# if isinstance( taskname, Task ):
			#	self.tasks[taskname.name] = taskname
			# 	taskkey = taskname.name
			# else:
			#	self.tasks[taskname] = Task( taskname )
			# 	taskkey = taskname
			#	return self.tasks[taskkey]
								
			regex = re.compile( '(%s_Node\d+$)' % task.name ).search					
			result = [ match.group(1) for l in self.tasks.globalNodeList for match  in [ regex(l) ] if match ]
			
			if result:
				result.sort()
				name, id = result[-1].split('_Node')
				
				task.name = '%s_Node%d' % ( name, int(id)+1 ) 
			else:
				task.name = '%s_Node1' % task.name							# rename the current task's name 
				
			self.tasks[ task.name ] = task
			key = task.name
			
		else:
			# Create a new task with impunity, appending "_Node" to the
			# end of the taskname. In this case 'task' is simply a string stating
			# the name of the task to create.
			
			# The taskname is the unique key for the node in the task tree
			
			regex = re.compile( '(%s_Node\d+$)' % task ).search					# search to see if the task name string provided matches a node
			result = [ m.group(1) for l in self.tasks.keys() for m  in [ regex(l) ] if m]		# it shouldn't be possible to match more that one, but it can happen so a list is built
			
			if result:
				result.sort()						
				name, id = result[-1].split('_Node')		
				
				task= '%s_Node%d' % ( name, int(id)+1 ) 	# if the taskname we've been given exists then we create a new node with an incremented indice.
			else:
				task = '%s_Node1' % task
			
			self.tasks[ task ] = Task( task )
			key = task
			
		self.tasks.globalNodeList.append( key )
		return self.tasks[ key ]
		
	def printme( self ):
		for task in self.tasks:
			print task, self.tasks[task].commands
			if    self.tasks[task].commands:
				print  "\t", self.tasks[task].commands[0].flags
			self.tasks[task].printme()

	
class Job( TaskTree ):
	"""Simplest way to think of this object is as the start of a job creation script. Global 
	parameters are set here which can effect all the children blah.
	"""
	
	def __init__( self, *args, **kwargs ):		
		self.after = "" 				# {month day hour:minute} or {hour:minute}
		self.atleast = 0
		self.atmost = 0
		self.globalvars = {}			# used in -init{}
		self.tags = []
		self.serialsubtasks = False	
		self.service = None
		self.tasks = OrderedDict()
		self.title = ""
		self.user = getpass.getuser()  
		self.environ = OrderedDict()
	
		if 'jobname' in kwargs:
			self.title = jobname
		elif len(args) == 1 :
			self.title = args[0]
			
	def assign( self, varname, value_string ):
		self.globalvars[varname] = value_string			
	
	def addEnvKey( self, key, value='' ):
		self.environ[key] = value
		
class Task( TaskTree ):
	# Task names are internally suffixed with "_NodeNNN". As such no
	# task should be named this way intentionally.
	
	def __init__( self, taskname, label="" ):
		self.name = taskname   
		self.label = label if label else taskname # -title{}
		
		self.cleanup = []
		self.chaser = ""
		self.commands = []    # -cmds{}
		self.preview = ""
		self.service  = None
		self.serialsubtasks = False
		self.tasks = OrderedDict()   # -subtasks{}
		self.instance = None
		
	@property
	def lastCmd( self ):
		try:
			return self.commands[-1]
		except:
			return None

	def addCmd( self, *args, **kwargs ):
		self.commands.append( Cmd() )
			
		if 'cmd' in kwargs:
			self.lastCmd.executable = kwargs['cmd'] 
		
		return self.lastCmd

	def addRemoteCmd( self, *args, **kwargs ):
		self.commands.append( RemoteCmd() )
		
		if 'cmd' in kwargs:
			self.lastCmd.executable = kwargs['cmd'] 
				
		if 'service' in kwargs:
			self.lastCmd.service = kwargs['service'] 
		
		return self.lastCmd
		
	def addChaser( self, executable, file ):
		pass
		
	def addPreview( self, executable, file ):
		pass
	
class Instance( Task ):
	def __init__(self, task):
		super(Instance, self).__init__("{0}_instance".format(task.name), task.label)
		self.instance = task.label

class Cmd( object ):
		
	def __init__( self, *args, **kwargs ):
		"""Simple execution command node. The executable can be passed
		a string containing the name of the program and any flags. Or the
		class can be subclassed for a specific program type."""
	
		self.atleast = 0
		self.executable = ""
		self.environ = OrderedDict()
		self.expand = False
		self.flags = list()
		self.grab = []
		self.id = ""
		self.ifcond =  ""
		self.metrics = ""
		self.refersto = ""
		self.remote = False
		self.retryrc = []
		self.samehost = False
		self.shell = ""
		self.tags = []
		
		for attr in self.__dict__:
			if attr in kwargs:
				if type( kwargs[attr] ) == type( self.__dict__[attr] ):
					self.__dict__[attr] = kwargs[attr]
	
	def addShell( self, shell ):
		self.shell = shell
	
	def addExecutable( self, executable ):
		self.executable = executable
	
	def addOption( self, flag, option='' ):
		if option:
			self.flags.append( (flag, str(option)) )
		else:
			self.flags.append( (flag, "") )
			
	def addPipe( self, executable, options='' ):
		if options:
			self.flags['|'] = ''
			self.flags[executable] = options
		else:
			self.flags['|'] = executable
			
	def addEnvKey( self, key, value='' ):
		self.environ[key] = value

class RemoteCmd( Cmd ):
	def __init__( self, *args, **kwargs ):
		Cmd.__init__(self, args, kwargs)
		self.remote = True

class Iterate( object ):
	def __init__(self):
		pass
	
