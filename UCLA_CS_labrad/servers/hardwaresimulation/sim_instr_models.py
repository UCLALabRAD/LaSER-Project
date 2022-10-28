

from twisted.internet.defer import inlineCallbacks, returnValue

class DeviceCommInterface(object):
    input_termination_char=None
    output_termination_char=None
    id_command=None
    id_string=None
    def __init__(self,dev,conn):
        self.input_buffer=bytearray(b'')
        self.dev=dev
        self.buffer_size=1000
        self.conn=conn
    
    @inlineCallbacks
    def read(self):
        pass
        
    
    def write(self):
        pass
        
    @inlineCallbacks
    def interpret_serial_command(self):
        pass
        
    @property
    def name(self):
        return self.dev.name
    @property
    def version(self):
        return self.dev.version
        
    @property
    def description(self):
        return self.dev.description
        
    @property
    def type(self):
        if issubclass(dev.cls,GPIBDeviceModel):
            return "GPIB"
        else:
            return "Serial"


        
    @buffer_size.setter
    def buffer_size(self,val):
        self.max_buffer_size=val
        if len(self.input_buffer)>self.max_buffer_size):
           temp=self.input_buffer
           self.input_buffer=bytearray(temp[:max_buffer_size])
           
            
            
        
    def reset_output_buffer(self):
        self.output_buffer=bytearray()
    def reset_input_buffer(self):
        self.input_buffer=bytearray()
    
        
class SerialDeviceCommInterface(DeviceCommInterface):
    input_termination_char=b'\r\n'
    output_termination_char=b'\n'
    
    
    def __init__(self,dev,conn):
        self.output_buffer=bytearray(b'')
        self.comm_baudrate=None
        self.comm_bytesize=None
        self.comm_parity=None
        self.comm_stopbits=None
        self.comm_dtr=None
        self.comm_rst=None
        self.conn=conn

    def enforce_correct_communication_parameters(self):
        if self.dev.actual_baudrate and self.comm_baudrate!= self.dev.actual_baudrate:
                self.dev.incorrect_comm_param_handle("baudrate")
        if self.dev.actual_bytesize and self.comm_bytesize!= self.dev.actual_bytesize:
                self.dev.incorrect_comm_param_handle("bytesize")
        if self.dev.actual_parity and self.comm_parity!= self.dev.actual_parity:
                self.dev.incorrect_comm_param_handle("parity")
        if self.dev.actual_stopbits and self.comm_stopbits!= self.dev.actual_stopbits:
                self.dev.incorrect_comm_param_handle("stopbits")
        if self.dev.actual_dtr and self.comm_dtr!= self.dev.actual_dtr:
                self.dev.incorrect_comm_param_handle("dtr")
        if self.dev.actual_rts and self.comm_rts!= self.dev.actual_rts:
                self.dev.incorrect_comm_param_handle("rts")
    
        
        
    @inlineCallbacks
    def interpret_serial_command(self, cmd):
        cmd,*args=cmd.split(" ")
        if (cmd,len(args)) not in self.dev.command_dict:
            pass #error
        elif not self.dev.command_dict[(cmd,len(args))]:
            pass
        else:
            resp= yield self.dev.command_dict[(cmd,len(args))](*args)
            returnValue(resp)
    
    @inlineCallbacks
    def read(self):
        *cmds, rest=self.dev.input_buffer.split(self.input_termination_byte)
        for cmd in cmds:
            command_interpretation=yield self.dev.interpret_serial_command(cmd)
            if len(self.output_buffer)+len(command_interpretation)>self.max_buffer_size:
                    self.output_buffer.extend(command_interpretation.encode()[:(self.max_buffer_size-len(self.output_buffer))])
            self.output_buffer.extend(command_interpretation.encode())
        resp=self.output_buffer.decode()
        return resp
        
    
    def write(self,data):
        if len(self.input_buffer)+len(data)>self.max_buffer_size:
            self.input_buffer.extend(data.encode()[:(self.max_buffer_size-len(self.input_buffer))])
            #buffer overflow error
        self.input_buffer.extend(data.encode())
        self.enforce_correct_communication_parameters()

        
 
        
        
class GPIBDeviceCommInterface(object):
    
    input_termination_char=""
    output_termination_char="\n"
    id_string=None
    def __init__(self):
        
    
        
    
    def check_if_scpi_match(self,cmd,cmd_scpi_format):
        cmd,*args=cmd.split(' ')
        cmd_format,num_args=cmd_format
        if not (len(args)==num_args):
            return False
        if (cmd[-1]=='?'):
            cmd=cmd[:-1]
        if not (cmd.lower()==cmd or cmd.upper()==cmd):
            return False
        cmd=cmd.lower()
        cmd_chunks_list=cmd.split(':')
        cmd_format_chunks_list=cmd_format.split(':')
        if len(cmd_chunks_list)!=len(cmd_format_chunks_list):
            return False
        for cmd_chunk,cmd_format_chunk in zip(cmd_chunks_list, cmd_format_chunks_list):
            prefix="".join([char for char in cmd_format_chunk if char.isupper()])
            prefix=prefix.lower()
            cmd_format_chunk=cmd_format_chunk.lower()
            if self.supports_any_prefix:
                if not (cmd_chunk.startswith(prefix) and cmd_format_chunk.startswith(cmd_chunk)):
                   return False
            else:
                if not (cmd_chunk==prefix or cmd_chunk==cmd_format_chunk):
                   return False
        return True
        
        
    @inlineCallbacks
    def interpret_serial_command(self, cmd):
        if cmd==self.id_command:
                returnValue(self.id_string)
        for cmd_specs, func in self.command_dict.items():
            if (self.is_valid_cmd(cmd,cmd_specs)):
                _,args_list=cmd.split(" ")
                args=args_list.split(',')
                if not func:
                    returnValue("")
                resp= yield func(*args)
                if resp:
                    returnValue(resp)
                else:
                    returnValue("")
        #error
        
    
class DeviceModel(object):
    def __init__(self):
        self.command_dict={}

    
class SerialDeviceModel(object):

    required_baudrate=None
    required_bytesize=None
    required_parity=None
    required_stopbits=None
    required_dtr=None
    required_rst=None

    def __init__(self):
        super().__init__()
    
    
    def handle_incorrect_connection_parameter(self,param,conn):
        pass
                
            
class GPIBDeviceModel(object):

    id_command="*IDN?"
    id_string=None
    
    def __init__(self):
        super().__init__()
        
        self.command_dict.extend{
        ("*IDN",0): (lambda: self.id_string)
        ("*CLS",0): (self.clear_buffers)
        ("*RST",0): self.start_with_defaults
        #anything with a star, the connection will be passed as well?
        }
        
        self.start_with_defaults()
  
    
    def start_with_defaults(self):
        pass
        
    def clear_buffers(self,conn):
        conn.input_buffer=bytearray()
        conn.output_buffer=bytearray()

            

                
