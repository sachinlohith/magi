#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.cli import CLI
import os
import time
from bottle import route, run, template

class MyTopo( Topo ):
    "Simple topology example."

    def build( self ):
        "Create custom topo."

        # Initialize topology
        #Topo.__init__( self )

        # Add hosts and switches
        leftHost = self.addHost( 'h1' )
	
        rightHost = self.addHost( 'h2' )
        
        # Add links
        self.addLink( leftHost, rightHost )
        
def perfTest():
	topo = MyTopo()
	net = Mininet(topo=topo)
	dumpNodeConnections(net.hosts)
	h1, h2 = net.getNodeByName('h1', 'h2')	
	
	@route('/cmd/<node>/<cmd>')
	def cmd( node='h1', cmd='hostname' ):
    		out, err, code = net.get( node ).pexec( cmd )
    		return out + err
	
	@route('/stop')
	def stop():
		net.stop()

	@route('/run_http_client/<value>')
	def function(value='1000'):	
		result = h2.cmd('curl -o /dev/null -s -S -w data=%{url_effective},%{time_total},%{time_starttransfer},%{size_download},%{speed_download}\n http://h1/getsize.py?length=' + value)
		print result
		return result
	
	@route('/goto_cli')
	def function():
		CLI(net)
		print "stopping"
		net.stop()
		return 0

	net.start()
	run(host='localhost', port=8080 )
	
	
if __name__ == '__main__':
    setLogLevel('info')
    perfTest()
