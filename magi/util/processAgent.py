#!/usr/bin/env python

from magi.daemon.processInterface import AgentInterface
from magi.util import config

import logging
import os
import socket
import sys

log = logging.getLogger(__name__)

def initializeProcessAgent(agent, argv):
    '''argv is assumed to have the following format. (This is usually set by the
    Magi daemon):

        agent_name agent_dock execute=[pipe|socket] (logfile=path)

    Where agent_name and agent_dock are strings and the key in the key=value
    pairs is literally the key given. The value may be restricted.
    '''
    if len(argv) < 3:
        log.critical('command line must start with name and dock')
        sys.exit(2)

    agent.name, dock = argv[1:3]
    args = argv_to_dict(argv[3:])
    
    setAttributes(agent, ['hostname', 'execute', 'logfile'], args)
    agent.docklist.add(dock)
    
    if not agent.logfile:
        agent.logfile = os.path.join('/tmp', agent.name + '.log')

    log_format = '%(asctime)s %(name)-12s %(levelname)-8s %(threadName)s %(message)s'
    log_datefmt = '%m-%d %H:%M:%S'
    handler = logging.FileHandler(agent.logfile, 'w')
    handler.setFormatter(logging.Formatter(log_format, log_datefmt))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = []
    root.addHandler(handler)

    log.info('argv: %s', argv)
    
    agent.commPort = config.getConfig().get('processAgentsCommPort')
    if not agent.commPort:
        agent.commPort = 18809
        
    infd, outfd = _getIOHandles(agent)
    agent.messenger = AgentInterface(infd, outfd, blocking=True)

    # Tell the daemon we want to listen on the dock. 
    # GTL - why doesn't the Daemon just associate the dock
    # with this process?
    agent.messenger.listenDock(dock)

    # now that we're connected, send an AgentLoaded message. 
    agent.messenger.trigger(event='AgentLoadDone', agent=agent.name, nodes=[agent.hostname])
    
    return args

def argv_to_dict(argv):
    '''Look for key=value pairs and convert them to a dictionary. 
    The set values are always strings. If you want a non-string type, 
    you must coerse it yourself after calling this function.'''
    result = dict()
    for arg in argv:
        words = arg.split('=')
        if len(words) == 2:
            log.debug('found key=value on command line.')
            result[words[0]] = words[1]
    return result
                
def _getIOHandles(agent):
    if not agent.execute:
        log.error('not told communication channel (pipe, socket), assuming socket.')
        agent.execute = 'socket'

    if agent.execute == 'pipe':
        return sys.stdin.fileno(), sys.stdout.fileno()
    
    elif agent.execute == 'socket':
        agent.magi_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        agent.magi_socket.connect(('localhost', agent.commPort))
        return agent.magi_socket.fileno(), agent.magi_socket.fileno()
    
    else:
        log.critical('unknown execute mode: %s. Unable to continue.')
        sys.exit(3)

def setAttributes(obj, argnames, dict):
    for arg in argnames:
        setattr(obj, arg, dict.get(arg))
        
