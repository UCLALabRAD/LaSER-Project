class SerialDeviceModel(object):

    required_baudrate=None
    required_bytesize=None
    required_parity=None
    required_stopbits=None
    required_dtr=None
    required_rst=None
    
    actual_baudrate=None
    actual_bytesize=None
    actual_parity=None
    actual_stopbits=None
    actual_dtr=None
    actual_rst=None
    
    command_dict=None
        
    def __init__(self):
        self.output_buffer=bytearray(b'')
        self.input_buffer=bytearray(b'')
   
    def interpret_serial_command(self, cmd):
        cmd,*args=cmd.split(" ")
        if (cmd,len(args)) not in self.command_dict:
            raise SimulatedDeviceError(0)
        elif not self.command_dict[(cmd,len(args))]:
            pass
        else:
            return self.command_dict[(cmd,len(args))](*args)
            
class GPIBDeviceModel(object):

    
    command_dict=None
    id_command="*IDN?"
    id_string=None
    supports_command_chaining=True
    supports_any_prefix=False
    def __init__(self):
        self.output_buffer=bytearray(b'')
        self.input_buffer=bytearray(b'')
        self.termination_character='\n'
   
    def interpret_serial_command(self, cmd):
        if cmd==self.id_command:
                return self.id_string
        for cmd_specs, func in self.command_dict.items():
            if (self.is_valid_cmd(cmd,cmd_specs)):
                _,*args=cmd.split(" ")
                resp=func(*args)
                if resp:
                    return resp
                else:
                    return ""
        return None
        
        
    def is_valid_cmd(self,cmd,cmd_format):
        cmd,*args=cmd.split(' ')
        cmd_format,num_args, query_option=cmd_format
        if not (len(args)==num_args or (query_option and len(args)==0)):
            return False
        if (query_option and cmd[-1]=='?'):
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
        
                
