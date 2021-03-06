
import logging
import os
import sys
import transportStream
from magimessage import MAGIMessage, DefaultCodec

log = logging.getLogger(__name__)
debug = False

class NoPipesOnOldCygwin(Exception):
	pass

class PipeBase(transportStream.StreamTransport):

	def __init__(self, fileobj=None, fd=None, codec=None):
		if 'ygwin' in sys.platform and sys.version_info[1] < 5:
			raise NoPipesOnOldCygwin()
		transportStream.StreamTransport.__init__(self, codec=codec, sock=None)
		self.fd = fd
		self.fileobj = fileobj
		self.connected = True
		if fileobj is not None:
			self.fd = self.fileobj.fileno()

	def close(self):
		if self.fileobj is not None:
			self.fileobj.close()
		else:
			os.close(self.fd)
		self.closed = True  # let upper levels know what happened
		
	def fileno(self):
		return self.fd

	def handle_close(self):
		log.info("closing %s", self)
		self.close()



class OutputPipe(PipeBase):
	""" This class implements the writing portion of a stream transport for a write only socket (pipe) """

	def __init__(self, fileobj=None, fd=None, codec=DefaultCodec):
		""" Create a new output pipe transport """
		PipeBase.__init__(self, fileobj=fileobj, fd=fd, codec=codec)

	@classmethod
	def fromFile(cls, filename):
		return OutputPipe(fd=os.open(filename, os.O_NONBLOCK | os.O_WRONLY))

	def handle_write(self):
		""" Override handle_write as we have a file descriptor, not a socket """
		if self.txMessage.isDone():
			try:
				msg = self.outmessages.pop(0)
				self.txMessage = transportStream.TXTracker(codec=self.codec, msg=msg)
			except IndexError:
				return
			
		if debug: log.log(2, "starting pipe write")
		#keep sending till you can
		while not self.txMessage.isDone():
			bytesWritten = os.write(self.fd, self.txMessage.getData())
			self.txMessage.sent(bytesWritten)
			#if no more can be written, break out
			if bytesWritten == 0:
				break
		if debug: log.log(2, "done pipe write")

	def __repr__(self):
		return "OutputPipe %d" % self.fileno()
	__str__ = __repr__

	def readable(self):
		""" Never reads """
		return False

	def handle_expt_event(self):
		# TODO: why is this occuring on output pipes?  Error set along with writable and everything keeps working
		# pass
		# Don't know what was occurring. Changed it to closing the pipe on exception.
		log.warning("Exception on %s", self)
		self.handle_close()



class InputPipe(PipeBase):
	""" This class implements the reading portion of a stream transport for a read only socket (pipe) """

	def __init__(self, fileobj=None, fd=None, codec=DefaultCodec):
		""" Create a new input pipe transport """
		PipeBase.__init__(self, fileobj=fileobj, fd=fd, codec=codec)

	@classmethod
	def fromFile(cls, filename):
		return InputPipe(fd=os.open(filename, os.O_NONBLOCK | os.O_RDONLY))

	def handle_read(self):
		""" Override handle_read as we have a file descriptor, not a socket """
		if debug: log.log(2, "starting pipe read")
		buf = os.read(self.fd, 4096)
		if buf == "":
			log.error("EOF on stream, file descriptor closed")
			raise IOError("EOF on stream, file descriptor closed")
		self.rxMessage.processData(buf)
		if debug: log.log(2, "done pipe read")
		while self.rxMessage.isDone():  # Extract all messages that are in the buffer
			if debug: log.debug("New message received on %s", self)
			self.inmessages.append(self.rxMessage.getMessage())
			self.rxMessage = transportStream.RXTracker(codec=self.codec, startbuf=self.rxMessage.getLeftover())

	def __repr__(self):
		return "InputPipe %d" % self.fd
	__str__ = __repr__

	def writable(self):
		""" Never writes """
		return False

	def handle_expt_event(self):
		log.warning("Exception on %s", self)
		self.handle_close()

