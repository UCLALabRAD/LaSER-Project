
from twisted.internet.defer import inlineCallbacks, returnValue, DeferredLock
from twisted.internet.threads import deferToThread
from datetime import datetime as dt

class SimulatedDeviceError(Exception):

    user_defined_errors={}
    
    base_error_dict={1: 'Trying to communicate with device with {} of {}; expected {}.',2: 'Command not recognized', 3: 'GPIB Query returned empty string.',4: 'Type of parameter {} is {} but should be {}', 5:'Value of {} for {} out of range'}
    def __init__(self, code,parameters=[]):
        self.code = code
        self.errorDict =dict(self.base_error_dict)
        self.errorDict.update(self.user_defined_errors)
        self.parameters=parameters
    
    

    def __str__(self):
        if self.code in self.errorDict:
            return self.errorDict[self.code].format(*self.parameters)
            

class DeviceCommInterface(object):

    
    def __init__(self,dev):
        self.input_buffer=bytearray(b'')
        self.output_buffer=bytearray(b'')
        self.dev=dev
        self.max_buffer_size=1000
        self.lock=DeferredLock()
        self.error_list=[]

 
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
    def channels(self):
        return self.dev.channels
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

    @property
    def buffer_size(self):
        return self.max_buffer_size
        
    @buffer_size.setter
    def buffer_size(self,val):
        self.max_buffer_size=val
        if len(self.input_buffer)>self.max_buffer_size:
           temp=self.input_buffer
           self.input_buffer=bytearray(temp[:max_buffer_size])
        self.max_buffer_size=val
        if len(self.output_buffer)>self.max_buffer_size:
           temp=self.output_buffer
           self.output_buffer=bytearray(temp[:max_buffer_size])


    def clear_buffers(self):
        self.reset_output_buffer()
        self.reset_input_buffer()        
            
            
        
    def reset_output_buffer(self):
        self.output_buffer=bytearray()
    def reset_input_buffer(self):
        self.input_buffer=bytearray()
    
    
    
    
    
    
    
    
        
class SerialDeviceCommInterface(DeviceCommInterface):

    
    
    def __init__(self,dev):
        super().__init__(dev)
        self.comm_baudrate=None
        self.comm_bytesize=None
        self.comm_parity=None
        self.comm_stopbits=None
        self.comm_dtr=None
        self.comm_rts=None
        

    
    
   
                
    
        
        
    
    def interpret_serial_command(self, cmd):
        self.dev.process_communication_parameters(self.comm_baudrate,self.comm_bytesize,self.comm_parity,self.comm_stopbits,self.comm_dtr,self.comm_rts)
        body,*args=cmd.split(b' ')
        for (spec_body,arg_counts),func in self.dev.command_dict.items():
            if type(arg_counts)==int:
                arg_counts=[arg_counts]
            if body==spec_body and len(args) in arg_counts:
                if func:
                    resp=self.dev.execute_command(func,[arg.decode() for arg in args])
                    return resp.encode()
                else:
                    return bytearray(b'')
                
        raise SimulatedDeviceError(2)
    

    def read(self,count=None):
        resp=None
        if count:
            resp,rest=self.input_buffer[:count],self.input_buffer[count:]
            self.input_buffer=self.input_buffer[count:]
        else:
            resp=self.input_buffer
            self.input_buffer=bytearray(b'')
            
        return resp
        
    @inlineCallbacks
    def write(self,data):
        if len(self.output_buffer)+len(data)>self.max_buffer_size:
            self.output_buffer.extend(data[:(self.max_buffer_size-len(self.output_buffer))])
            #buffer overflow error
        else:
            self.output_buffer.extend(data)
        yield self.process_commands()
        

    @inlineCallbacks
    def process_commands(self):
        *cmds, rest=self.output_buffer.split(self.dev.input_termination_byte)
        self.output_buffer=rest
        for cmd in cmds:
            command_interpretation=None
            try:
                command_interpretation= yield deferToThread(lambda:self.interpret_serial_command(cmd))
                #if len(self.output_buffer)+len(command_interpretation)>self.max_buffer_size:
                    #self.output_buffer.extend(command_interpretation.encode()[:(self.max_buffer_size-len(self.output_buffer))])
                    #error
            except SimulatedDeviceError as e:
                self.error_list.append((str(dt.now()),cmd.decode(),str(e)))
                
            
            else:
                if command_interpretation:
                    command_interpretation=command_interpretation+self.dev.output_termination_byte
                self.input_buffer.extend(command_interpretation)
        

        
 
        
        
        
        
        
class GPIBDeviceCommInterface(DeviceCommInterface):
    

    id_string=None
    
        
    
        
    def expand_chained_commands(self,cmd):
        cmd=cmd.decode()
        keywords=cmd.split(':')
        tree=[keyword.split(';') for keyword in keywords]
        full_msg=[]
        self.collect_paths(tree,[],full_msg)
        return full_msg


    def collect_paths(self,tree,current_path,path_collector):
        if len(current_path)==len(tree):
            path_collector.append(bytearray(':'.join(current_path).encode()))
        else:
            for i in tree[len(current_path)]:
                self.collect_paths(tree,current_path+[i],path_collector)


    def check_if_scpi_match(self,cmd,cmd_scpi_format):

        pieces=cmd.split(b' ')
        body=pieces[0]
        args=None
        if len(pieces)>1:
            args=pieces[1]
        args_list=[]
        if args:
           args_list=args.split(b',')
        body_format,arg_nums=cmd_scpi_format
        body=body.decode()
        body_format=body_format.decode()
        if body_format[0]==':':
           body_format=body_format[1:]
        if body[-1]=='?' and body_format[-1]=='?':
            body=body[:-1]
            body_format=body_format[:-1]
        body_format=body_format.replace('[:',':[')
        if type(arg_nums)==int:
            arg_nums=[arg_nums]
        if not (len(args_list) in arg_nums):
            return False
        if not (body.lower()==body or body.upper()==body):
            return False
        
        body=body.lower()
        body_chunks_list=body.split(':')
        body_format_chunks_list=body_format.split(':')
        rem_block=[]
        rem_block_format=[]
        
                    
        index_in_format=0
        for body_chunk in body_chunks_list:
            
            while True:
                if index_in_format>=len(body_format_chunks_list):
                    return False
                body_format_chunk=body_format_chunks_list[index_in_format]
                can_skip=False
                if body_format_chunk[0]=='[' and body_format_chunk[-1]==']':
                    can_skip=True
                    body_format_chunk=body_format_chunk[1:-1]
                prefix=''.join([char for char in body_format_chunk if char.isupper() or char.isnumeric()])
                prefix=prefix.lower()
                body_format_chunk=body_format_chunk.lower()
                # if self.supports_any_prefix:
                #      if not (cmd_chunk.startswith(prefix) and cmd_format_chunk.startswith(cmd_chunk)):
                #        return False
                if not (body_chunk==prefix or body_chunk==body_format_chunk):
                   if can_skip:
                       index_in_format=index_in_format+1
                   else:
                       return False
                else:
                   index_in_format=index_in_format+1
                   break
        for rem_body_format_chunk in body_format_chunks_list[index_in_format:]:
            if body_format_chunk[0]!='[' or body_format_chunk[-1]!=']':
                    return False
        return True


    def interpret_serial_command(self, cmd):
        #query vs setting vs default
        if cmd.decode()[0]=='*':
            if cmd==self.dev.id_command:
                return self.dev.id_string
            elif cmd==self.dev.clear_command:
                self.clear_buffers()
                return None
            elif cmd==self.dev.reset_command:
                self.dev.set_default_settings()
                return
            else:
                pass
                
                
        else:
            is_query=False
            if cmd.split(b' ')[0].decode()[-1]=='?':
                is_query=True
            for cmd_specs, func in self.dev.command_dict.items():
                if (self.check_if_scpi_match(cmd,cmd_specs)):
                    
                    pieces=cmd.split(b' ')
                    body=pieces[0]
                
                    args=None
                    if len(pieces)>1:
                        args=pieces[1]
                    args_list=[]
                    if args:
                        args_list=args.split(b',')
                    if not func:
                        return
                    if is_query:
                        
                        resp= self.dev.execute_command(func,[arg.decode() for arg in args_list])
                        if resp:
                            return resp.encode()
                        else:
                            raise Exception()
                    
                    else:
                        self.dev.execute_command(func,[arg.decode() for arg in args_list])
                        return
            raise Exception()
            
        
        
    def read(self,count=None):
        resp=None
        if count:
            resp,rest=self.input_buffer[:count],self.input_buffer[count:]
            self.input_buffer=self.input_buffer[count:]
        else:
            resp=self.input_buffer
            self.input_buffer=bytearray(b'')
            
        return resp
        
    @inlineCallbacks
    def write(self,data):
        
        if data[:1].decode()==':':
            data=data[1:]

        if len(self.output_buffer)+len(data)>self.max_buffer_size:
            self.output_buffer.extend(data[:(self.max_buffer_size-len(self.output_buffer))])
            #buffer overflow error
        else:
            self.output_buffer.extend(data)
        yield self.process_commands()
            
        
    @inlineCallbacks
    def process_commands(self):
        self.input_buffer=bytearray(b'')
        chained_cmds =self.output_buffer.split(self.dev.input_termination_byte)
        self.output_buffer=bytearray(b'')
        expanded_commands=[]
        for chained_cmd in chained_cmds:
            expanded_commands.extend(self.expand_chained_commands(chained_cmd))
        for cmd in expanded_commands:
            command_interpretation=None
            try:
                command_interpretation= yield deferToThread(lambda:self.interpret_serial_command(cmd))
                #if len(self.output_buffer)+len(command_interpretation)>self.max_buffer_size:
                    #self.output_buffer.extend(command_interpretation.encode()[:(self.max_buffer_size-len(self.output_buffer))])
                    #error
            except SimulatedDeviceError as e:
                self.error_list.append((str(dt.now()),cmd.decode(),str(e)))
            
            else:
                if command_interpretation:
                    self.input_buffer.extend(command_interpretation+self.dev.output_termination_byte)
                
        
        if self.input_buffer:
            
            self.input_buffer=self.input_buffer[:-1]
            self.input_buffer.extend(b'\n')

                
            
    
    
    
    
    
class DeviceModel(object):
    command_dict=None
    
    input_termination_byte=None
    output_termination_byte=None
    id_command=None
    id_string=None
    
    def set_default_settings(self):
        pass
    
    def execute_command(self,func,args):
        return func(self,*args)
    
class SerialDeviceModel(DeviceModel):


    input_termination_byte=b'\r\n'
    output_termination_byte=b'\n'
    
    required_baudrate=None
    required_bytesize=None
    required_parity=None
    required_stopbits=None
    required_dtr=None
    required_rts=None

    command_dict=None

    
        
    def set_default_settings(self):
        pass
        
    def process_communication_parameters(self,baudrate,bytesize,parity,stopbits,dtr,rts):
        if self.required_baudrate and baudrate!= self.required_baudrate:
                raise SimulatedDeviceError(1,["baudrate",baudrate,self.required_baudrate])
        if self.required_bytesize and bytesize!= self.required_bytesize:
                raise SimulatedDeviceError(1,["bytesize",bytesize,self.required_bytesize])
        if self.required_parity and parity!= self.required_parity:
                raise SimulatedDeviceError(1,["parity",parity,self.required_parity])
        if self.required_stopbits and stopbits!= self.required_stopbits:
                raise SimulatedDeviceError(1,["stopbits",stopbits,self.required_stopbits])
        if self.required_dtr and dtr!= self.required_dtr:
                raise SimulatedDeviceError(1,["dtr",dtr,self.required_dtr])
        if self.required_rts and rts!= self.required_rts:
                raise SimulatedDeviceError(1,["rts",rts,self.required_rts])

        
                
            
class GPIBDeviceModel(DeviceModel):

    input_termination_byte=b';:'
    output_termination_byte=b';'
    
    id_command=b'*IDN?'
    clear_command=b'*CLS'
    reset_command=b'*RST'
    id_string=None
    
    command_dict=None

    def set_default_settings(self):
        pass

            

                
