

from twisted.internet.defer import inlineCallbacks, returnValue

class DeviceCommInterface(object):
    input_termination_char=None
    output_termination_char=None
    id_command=None
    id_string=None
    max_buffer_size=None
    
    def __init__(self,dev,conn):
        self.input_buffer=bytearray(b'')
        self.output_buffer=bytearray(b'')
        self.dev=dev

    
 
    def read(self):
        pass
        
    
    def write(self):
        pass
        
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
    
        
        
    
    def interpret_serial_command(self, cmd):
        body,*args=cmd.split(b' ')
        for (spec_body,arg_counts),func in self.dev.command_dict.items():
            if type(arg_counts)==str:
                arg_counts=[arg_counts]
            if body==spec_body and len(args) in arg_counts:
                if func:
                    resp=func(*args)
                else:
                    return bytearray(b'')
                
        #Error if in debug mode?
        return bytearray(b'')
    

    def read(self,count=None):
        resp=None
        if count:
            resp,rest=self.output_buffer[:count],self.output_buffer[count:]
            self.output_buffer=self.output_buffer[count:]
        else:
            resp=self.output_buffer
            self.output_buffer=bytearray(b'')
            
        return resp
        
    
    def write(self,data):
        if len(self.input_buffer)+len(data)>self.max_buffer_size:
            self.input_buffer.extend(data[:(self.max_buffer_size-len(self.input_buffer))])
            #buffer overflow error
        else:
            self.input_buffer.extend(data)
        self.enforce_correct_communication_parameters()
        self.process_commands()
        
    def process_commands(self):
        *cmds, rest=self.dev.input_buffer.split(self.input_termination_byte)
        for cmd in cmds:
            try:
                command_interpretation= self.interpret_serial_command(cmd)
                #if len(self.output_buffer)+len(command_interpretation)>self.max_buffer_size:
                    #self.output_buffer.extend(command_interpretation.encode()[:(self.max_buffer_size-len(self.output_buffer))])
                    #error
            except:
                #if debug mode, error
                break
            
            else:
                self.output_buffer.extend(command_interpretation+output_termination_char)
        

        
 
        
        
        
        
        
class GPIBDeviceCommInterface(object):
    
    input_termination_char=b':;'
    output_termination_char=b';'
    id_string=None
    
        
    
        
    def expand_chained_commands(self,cmd):
        keywords=cmd.split(b':')
        tree=[keyword.split(b';') for keyword in keywords]
        full_msg=[]
        self.collect_paths(tree,[],full_msg)
        return full_msg


    def collect_paths(tree,current_path,path_collector)
        if len(current_path)==len(tree):
            self.path_collector.append(current_path.join(b':'))
        else:
            for i in paths[len(current_path)]:
                expand_node(tree,current_path+[i],path_collector)


    def check_if_scpi_match(self,cmd,cmd_scpi_format):
        cmd=str(cmd)
        cmd_scpi_format=str(cmd_scpi_format)
       
        body,args_list=cmd.split(b' ')
        args=args_list.split(b',')
        if body[-1]=='?' and body_format[-1]==b'?':
            body=body[:-1]
            body_format=body_format[:-1]
        body_format,arg_nums=cmd_format
        body_format.replace(b'[:',':[')
        
        if type(arg_nums)==str:
            arg_nums=[arg_nums]
        if not (len(args) in arg_nums):
            return False
        if not (body.lower()==body or body.upper()==body):
            return False
        body=body.lower()
        body_chunks_list=body.split(':')
        body_format_chunks_list=body_format.split(':')
        if len(body_chunks_list)!=len(body_format_chunks_list):
            return False
        rem_block=[]
        rem_block_format=[]
        for index, (body_chunk,body_format_chunk) in enumerate(zip(body_chunks_list, body_format_chunks_list)):
            if body_format_chunk[0]=='[' and body_format_chunk[-1]==']':
                prefix=''.join([char for char in body_format_chunk if char.isupper()])
                prefix=prefix.lower()
                body_format_chunk=body_format_chunk.lower()
          # if self.supports_any_prefix:
          #      if not (cmd_chunk.startswith(prefix) and cmd_format_chunk.startswith(cmd_chunk)):
           #        return False
                if not (body_chunk==prefix or body_chunk==cmd_format_chunk):
                    rem_block_format.append(i)
                else:
                    rem_block.append(i)
                    rem_block_format.append(i)
            else:
                    rem_block.append(i)
                    rem_block_format.append(i)
                    
        body_chunks_list=[body_chunks_list[i] for i in len(body_chunks_list) if i not in rem_block]
        body_format_chunks_list=[body_format_chunks_list[i] for i in len(body_format_chunks_list) if i not in rem_block_format]
        
        for body_chunk,body_format_chunk in zip(body_chunks_list, body_format_chunks_list):
            prefix=''.join([char for char in body_format_chunk if char.isupper()])
            prefix=prefix.lower()
            body_format_chunk=body_format_chunk.lower()
          # if self.supports_any_prefix:
          #      if not (cmd_chunk.startswith(prefix) and cmd_format_chunk.startswith(cmd_chunk)):
           #        return False
            if not (body_chunk==prefix or body_chunk==cmd_format_chunk):
               return False
        return True


    def interpret_serial_command(self, cmd):
        #query vs setting vs default
        if cmd[0]==b'*':
            if cmd==self.dev.id_command:
                return self.dev.id_string
            elif cmd==self.dev.clear_command:
                self.clear_buffers()
                return None
            elif cmd==self.dev.reset_command:
                self.dev.set_to_default()
                return
            else:
                
                
        else:
            is_query=False
            if cmd.split(b' ')[0][-1]=='?':
                is_query=True
            for cmd_specs, func in self.command_dict.items():
                if (self.check_if_scpi_match(cmd,cmd_specs)):
                    _,args_list=cmd.split(b' ')
                    args=args_list.split(b',')
                    if not func:
                            return b''
                    if is_query:
                        resp= func(*args)
                        if resp:
                            return resp
                        else:
                            #error
                    
                    else:
                        func(*args)
                        return b''
            #error
            
        
        
    def read(self,count=None):
        resp=None
        if count:
            resp,rest=self.output_buffer[:count],self.output_buffer[count:]
            self.output_buffer=self.output_buffer[count:]
        else:
            resp=self.output_buffer
            self.output_buffer=bytearray(b'')
            
        return resp
        
    
    def write(self,data):
        if data[0]==b':':
            data=data[1:]
        if len(self.input_buffer)+len(data)>self.max_buffer_size:
            self.input_buffer.extend(data[:(self.max_buffer_size-len(self.input_buffer))])
            #buffer overflow error
        else:
            self.input_buffer.extend(data)
        self.process_commands()
            
        
    
    def process_commands(self):
        self.output_buffer=bytearray(b'')
        *chained_cmds, rest=self.dev.input_buffer.split(self.input_termination_byte)
        expanded_commands=[]
        for chained_cmd in chained_cmds:
            expanded_commands.extend(self.expand_chained_commands(chained_cmd))
        for cmd in expanded_commands:
            try:
                command_interpretation= self.interpret_serial_command(cmd)
                #if len(self.output_buffer)+len(command_interpretation)>self.max_buffer_size:
                    #self.output_buffer.extend(command_interpretation.encode()[:(self.max_buffer_size-len(self.output_buffer))])
                    #error
            except:
                self.output_buffer=bytearray(b'')
                #if debug mode, error
                break
            
            else:
                self.output_buffer.extend(command_interpretation+output_termination_char)
        if self.output_buffer:
            self.output_buffer.append(b'\n')

                
                
            
    
    
    
    
    
    
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

            

                
