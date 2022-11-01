from pyvisa.highlevel import VisaLibraryBase
from pyvisa.resources.resource import Resource
import contextlib
import struct
import time
import warnings
from typing import Any, Callable, Iterable, Iterator, Optional, Sequence, Type, Union

from pyvisa import attributes, constants, errors, logger, util
from pyvisa.attributes import Attribute

from twisted.internet.defer import returnValue, inlineCallbacks, DeferredLock

class SimulatedDeviceVisaLibrary(VisaLibraryBase):
        
    def _init(self):
        self.node=None
        self.cli=None
        self.ser=None
        self.sim_addresses=None

    def open_default_resource_manager(self):
        return "DefaultResourceManagerSession", constants.StatusCode.success
        
    def list_resources(self,session,query='?*::INSTR'):
        return tuple(self.sim_addresses)

    def open(self, session, resource_name,
             access_mode=None, open_timeout=None):
        instr_session=self.cli.context()
        self.ser.select_device(self.node, resource_name,context=instr_session)
        
        return instr_session, constants.StatusCode.success

    def close(self, session):
        """Closes the specified session, event, or find list.

        Corresponds to viClose function of the VISA library."""
        if session=="DefaultResourceManagerSession":
            return constants.StatusCode.success

        else:
            return constants.StatusCode.success
            
    @inlineCallbacks
    def read(self,session,count): 
            resp=yield self.read(count,context=session)
            #if count and len(resp) < count:
               # raise errors.VisaIOError(constants.StatusCode.error_timeout)
            returnValue((resp.encode(),constants.StatusCode.success))

            

    @inlineCallbacks
    def write(self,session,data):
        bytes=yield self.ser.gpib_write(data.decode(),context=session)
        returnValue((bytes,constants.StatusCode.success))
        

        
    def get_attribute(self,session,attribute):
        if session=="DefaultResourceManagerSession":
            return getattr(self,attribute), constants.StatusCode.success
        else:
            return 1,  constants.StatusCode.success
                
    def set_attribute(self,session,attribute,attribute_state):
        if session=="DefaultResourceManagerSession":
            if hasattr(self,attribute):
                setattr(self,attribute,attribute_state)
        return constants.StatusCode.success
    
    
    def clear(self,session):
        self.ser.reset_input_buffer(context=session)
        self.ser.reset_output_buffer(context=session)
        return constants.StatusCode.success
    
    
        
            
                
                
             
class AsyncMessageBasedResource(Resource):
    """Base class for resources that use message based communication."""

    CR  = "\r"
    LF  = "\n"

    #: Number of bytes to read at a time. Some resources (serial) may not support
    #: large chunk sizes.
    chunk_size = 20 * 1024

    #: Delay in s to sleep between the write and read occuring in a query
    query_delay  = 0.0

    #: Internal storage for the read_termination character
    _read_termination = None

    #: Internal storage for the write_termination character
    _write_termination = CR + LF

    #: Internal storage for the encoding
    _encoding = "ascii"

    @property
    def encoding(self):
        """Encoding used for read and write operations."""
        return self._encoding

    @encoding.setter
    def encoding(self, encoding: str):
        # Test that the encoding specified makes sense.
        "test encoding".encode(encoding).decode(encoding)
        self._encoding = encoding

    @property
    def read_termination(self):
        """Read termination character."""
        return self._read_termination

    @read_termination.setter
    def read_termination(self, value):

        if value:
            # termination character, the rest is just used for verification
            # after each read operation.
            last_char = value[-1:]
            # Consequently, it's illogical to have the real termination
            # character twice in the sequence (otherwise reading would stop
            # prematurely).

            if last_char in value[:-1]:
                raise ValueError("ambiguous ending in termination characters")

            self.set_visa_attribute(
                constants.ResourceAttribute.termchar, ord(last_char)
            )
            self.set_visa_attribute(
                constants.ResourceAttribute.termchar_enabled, constants.VI_TRUE
            )
        else:
            # The termchar is also used in VI_ATTR_ASRL_END_IN (for serial
            # termination) so return it to its default.
            self.set_visa_attribute(constants.ResourceAttribute.termchar, ord(self.LF))
            self.set_visa_attribute(
                constants.ResourceAttribute.termchar_enabled, constants.VI_FALSE
            )

        self._read_termination = value

    @property
    def write_termination(self):
        """Write termination character."""
        return self._write_termination

    @write_termination.setter
    def write_termination(self, value):
        self._write_termination = value


    
    @inlineCallbacks
    def write_raw(self, message: bytes):
        """Write a byte message to the device.

        Parameters
        ----------
        message : bytes
            The message to be sent.

        Returns
        -------
        int
            Number of bytes written

        """
        resp=yield self.visalib.write(self.session, message)
        returnValue(resp[0])

    @inlineCallbacks
    def write(
        self,
        message,
        termination = None,
        encoding = None,
    ):
        """Write a string message to the device.

        The write_termination is always appended to it.

        Parameters
        ----------
        message : str
            The message to be sent.
        termination : Optional[str], optional
            Alternative character termination to use. If None, the value of
            write_termination is used. Defaults to None.
        encoding : Optional[str], optional
            Alternative encoding to use to turn str into bytes. If None, the
            value of encoding is used. Defaults to None.

        Returns
        -------
        int
            Number of bytes written.

        """
        term = self._write_termination if termination is None else termination
        enco = self._encoding if encoding is None else encoding

        if term:
            if message.endswith(term):
                warnings.warn(
                    "write message already ends with " "termination characters",
                    stacklevel=2,
                )
            message += term

        count = yield self.write_raw(message.encode(enco))

        returnValue(count)

    @inlineCallbacks
    def read_bytes(
        self,
        count,
        chunk_size = None,
        break_on_termchar = False,
    ):
        """Read a certain number of bytes from the instrument.

        Parameters
        ----------
        count : int
            The number of bytes to read from the instrument.
        chunk_size : Optional[int], optional
            The chunk size to use to perform the reading. If count > chunk_size
            multiple low level operations will be performed. Defaults to None,
            meaning the resource wide set value is set.
        break_on_termchar : bool, optional
            Should the reading stop when a termination character is encountered
            or when the message ends. Defaults to False.

        Returns
        -------
        bytes
            Bytes read from the instrument.

        """
        chunk_size = chunk_size or self.chunk_size
        ret = bytearray()
        left_to_read = count
        success = constants.StatusCode.success
        termchar_read = constants.StatusCode.success_termination_character_read

        with self.ignore_warning(
            constants.StatusCode.success_device_not_present,
            constants.StatusCode.success_max_count_read,
        ):
            try:
                status = None
                while len(ret) < count:
                    size = min(chunk_size, left_to_read)
                    logger.debug(
                        "%s - reading %d bytes (last status %r)",
                        self._resource_name,
                        size,
                        status,
                    )
                    chunk, status = yield self.visalib.read(self.session, size)
                    ret.extend(chunk)
                    left_to_read -= len(chunk)
                    if break_on_termchar and (
                        status == success or status == termchar_read
                    ):
                        break
            except errors.VisaIOError as e:
                logger.debug(
                    "%s - exception while reading: %s\n" "Buffer content: %r",
                    self._resource_name,
                    e,
                    ret,
                )
                raise
        returnValue(bytes(ret))
    @inlineCallbacks
    def read_raw(self, size = None):
        """Read the unmodified string sent from the instrument to the computer.

        In contrast to read(), no termination characters are stripped.

        Parameters
        ----------
        size : Optional[int], optional
            The chunk size to use to perform the reading. Defaults to None,
            meaning the resource wide set value is set.

        Returns
        -------
        bytes
            Bytes read from the instrument.

        """
        resp=yield self._read_raw(size)
        returnValue(bytes(resp))

    @inlineCallbacks
    def _read_raw(self, size  = None):
        """Read the unmodified string sent from the instrument to the computer.

        In contrast to read(), no termination characters are stripped.

        Parameters
        ----------
        size : Optional[int], optional
            The chunk size to use to perform the reading. Defaults to None,
            meaning the resource wide set value is set.

        Returns
        -------
        bytearray
            Bytes read from the instrument.

        """
        size = self.chunk_size if size is None else size

        loop_status = constants.StatusCode.success_max_count_read

        ret = bytearray()
        with self.ignore_warning(
            constants.StatusCode.success_device_not_present,
            constants.StatusCode.success_max_count_read,
        ):
            try:
                status = loop_status
                while status == loop_status:
                    logger.debug(
                        "%s - reading %d bytes (last status %r)",
                        self._resource_name,
                        size,
                        status,
                    )
                    chunk, status = yield self.visalib.read(self.session, size)
                    ret.extend(chunk)
            except errors.VisaIOError as e:
                logger.debug(
                    "%s - exception while reading: %s\nBuffer " "content: %r",
                    self._resource_name,
                    e,
                    ret,
                )
                raise

        returnValue(ret)

    @inlineCallbacks
    def read(
        self, termination = None, encoding = None
    ):
        """Read a string from the device.

        Reading stops when the device stops sending (e.g. by setting
        appropriate bus lines), or the termination characters sequence was
        detected.  Attention: Only the last character of the termination
        characters is really used to stop reading, however, the whole sequence
        is compared to the ending of the read string message.  If they don't
        match, a warning is issued.

        Parameters
        ----------
        termination : Optional[str], optional
            Alternative character termination to use. If None, the value of
            write_termination is used. Defaults to None.
        encoding : Optional[str], optional
            Alternative encoding to use to turn bytes into str. If None, the
            value of encoding is used. Defaults to None.

        Returns
        -------
        str
            Message read from the instrument and decoded.

        """
        enco = self._encoding if encoding is None else encoding

        if termination is None:
            termination = self._read_termination
            message = yield self._read_raw()
            message=message.decode(enco)
        else:
            with self.read_termination_context(termination):
                message = yield self._read_raw()
                message=message.decode(enco)

        if not termination:
            returnValue(message)

        if not message.endswith(termination):
            warnings.warn(
                "read string doesn't end with " "termination characters", stacklevel=2
            )
            returnValue(message)

        returnValue(message[: -len(termination)])




    @inlineCallbacks
    def query(self, message: str, delay: Optional[float] = None):
        """A combination of write(message) and read()

        Parameters
        ----------
        message : str
            The message to send.
        delay : Optional[float], optional
            Delay in seconds between write and read operations. If None,
            defaults to self.query_delay.

        Returns
        -------
        str
            Answer from the device.

        """
        yield self.write(message)

        delay = self.query_delay if delay is None else delay
        if delay > 0.0:
            time.sleep(delay)

        count=yield self.read()
        returnValue(count)


    
    @inlineCallbacks
    def flush(self, mask: constants.BufferOperation):
        """Manually clears the specified buffers.

        Depending on the value of the mask this can cause the buffer data
        to be written to the device.

        Parameters
        ----------
        mask : constants.BufferOperation
            Specifies the action to be taken with flushing the buffer.
            See highlevel.VisaLibraryBase.flush for a detailed description.

        """
        resp=yield self.visalib.flush(self.session, mask)
        returnValue(resp)
        
        
WRAPPER_CLASS=SimulatedDeviceVisaLibrary
