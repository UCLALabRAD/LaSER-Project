from twisted.internet.defer import inlineCallbacks, returnValue, DeferredLock
from twisted.internet.threads import deferToThread


from datetime import datetime as dt

from UCLA_CS_labrad.servers.hardwaresimulation.simulatedinstruments.simulated_instruments import SimulatedGPIBInstrumentInterface, SimulatedSerialInstrumentInterface,SimulatedInstrumentError


#A real instrument has a lot of properties: its inner scientific functionality, the commands it accepts, its buffers, its encoding/decoding methods, and more.
#This can be split into two types of properties: communication-related properties, which are shared by all devices with the same connection type
#(although for some such properties, values may change by device), and properties that are specific to device types based on their functionality.
#The former will never need to be modified and would be painful for users to write code for.
#Instead, this should be part of a communication-focused device wrapper between the HSS client and the internal functionality of the device they’ve selected.
#So, when a user adds a simulated device in the HSS, an object of the specified class is instantiated, and placed into a GPIBCommunicationWrapper or SerialCommunicationWrapper
# based on whether the class was a SimulatedSerialDeviceInterface subclass or a SimulatedGPIBDeviceInterface subclass, before being stored in the HSS' wrapped devices dictionary.
class SimulatedCommunicationInterface(object):

    
    def __init__(self,dev):
    
        #each wrapper type has bytearrays (which can be extended and split by a specified byte pattern easily, just like strings) for
        #input_ and output_buffers (named from the perspective of the client, not the device)
        self.input_buffer=bytearray(b'')
        self.output_buffer=bytearray(b'')
        
        #simulated device instantiated from the user-written specific device class.
        self.dev=dev
        
        #max buffer size for both input and output buffers
        self.max_buffer_size=1000
        
        #twisted lock for device to be locked/released before/after calling a communication wrapper method (see HSS file and interpret_serial_command for info about locking)
        self.lock=DeferredLock()
        
        #error queue for device (see HSS for more info)
        self.error_list=[]

 
    #read from input buffer. TODO: same for serial and gpib wrappers so far, so may want to just move the logic here to avoid code duplication
    def read(self):
        pass
        
    #write to output buffer. see HSS simulated_write setting
    def write(self):
        pass
        
    #interpret_command takes care of the process in which the SerialCommunicationWrapper checks if its simulated_device supports the command (via the command dict),
    #feeds the command to the device if so, and gets the response if there is one. During the process of writing the HSS, we decided to promote scalability by having
    # Twisted allocate separate threads to handle the interpretation of each command sent to each simulated device, using deferToThread. Thus, the
    #reactor thread’s job is to get commands from clients to devices, start threads, and get devices’ responses back to clients, while all the functionality
    #written by the user in generic device classes would be run in separate threads. If we didn’t do this, a client making a HSS request would have to wait
    #for all the commands in every simulated device’s input buffer to be handled sequentially before the server could handle their request. This way, devices
    #have their own “processors” and we can yield each defertoThread call so while a command is being interpreted and handled by a device, the HSS can focus
    #on its other clients, getting commands to other devices (or responses from them) and starting other threads in other devices. The HSS would theoretically be run on a computer with a lot
    #of cores that can handle a lot of threads, as Twisted decides on the size of its thread pool based on the hardware the server is running on. The DeferredLock
    #will ensure that no more than one thread is acting on a wrapped device at a time (as only one client can get inside the wrapper of a device at a time).
    def interpret_serial_command(self):
        pass
       
    #use property decorator so HSS code can read these properties of the device class, as if they were properties of the wrapper
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
        #if specific device class of wrapped device is subclass of GPIBInstrument, it's a GPIB device. Otherwise it's a serial device.
        #property decorator used to make it easier to check communication type for wrapped device
        if issubclass(type(self.dev),SimulatedGPIBInstrumentInterface):
            return "GPIB"
        else:
            return "Serial"

    #property decorator used for getters/setters so HSS can treat max buffer size as if it were just a property of wrapper, but in reality when it's set more logic can be executed
    @property
    def buffer_size(self):
        return self.max_buffer_size
        
    @buffer_size.setter
    def buffer_size(self,val):
        self.max_buffer_size=val
        if len(self.input_buffer)>self.max_buffer_size:
           temp=self.input_buffer
           self.input_buffer=bytearray(temp[:self.max_buffer_size]) #remove any bytes beyond new max buffer size
        self.max_buffer_size=val
        if len(self.output_buffer)>self.max_buffer_size:
           temp=self.output_buffer
           self.output_buffer=bytearray(temp[:self.max_buffer_size])


    def clear_buffers(self):
        self.reset_output_buffer()
        self.reset_input_buffer()
            
            
        
    def reset_output_buffer(self):
        self.output_buffer=bytearray()
    def reset_input_buffer(self):
        self.input_buffer=bytearray()
    
    
    
    
    
    
    
    
#communication wrapper for serial devices
class SimulatedSerialCommunicationInterface(SimulatedCommunicationInterface):

    
    def __init__(self,dev):
        super().__init__(dev)
        #declare serial communication parameters used to communicate with device.
        self.comm_baudrate=None
        self.comm_bytesize=None
        self.comm_parity=None
        self.comm_stopbits=None
        self.comm_dtr=None
        self.comm_rts=None
        

    
    
   
                
    
        
        
    
    def interpret_serial_command(self, cmd):
        #first gives the values of its serial communication parameters to the device. If the simulated device refuses to accept these parameters
        #it will react in some way (this is decided upon by the writer of the specific device class). See SimulatedSerialInstrument for default behavior.
        self.dev.process_communication_parameters(self.comm_baudrate,self.comm_bytesize,self.comm_parity,self.comm_stopbits,self.comm_dtr,self.comm_rts)
        #Assuming no trouble here, the wrapper splits the command into the header of the command and the arguments.
        body,*args=cmd.split(b' ')
        
        #It then checks the valid command headers in the device’s command_dict  (a Python dictionary written by the specific-device-writer mapping
        #specific-device command headers to generic-device handler methods), to see if the command matches any of them.
        for (spec_body,arg_counts),func in self.dev.command_dict.items():
            if type(arg_counts)==int:
                arg_counts=[arg_counts] #list of valid numbers of arguments for this command in command dict
            if body==spec_body and len(args) in arg_counts: #match found in command dict (header matches and number of arguments provided supported for that command header)
                if func:
                    resp=self.dev.execute_command(func,[arg.decode() for arg in args]) #If so, the generic-device functionality (a method) that was attached to that command header when writing the device’s command_dict will be called, with the command’s arguments being passed to the method.
                    return resp.encode()
                else:
                    return bytearray(b'') #If matching key in command_dict maps to None, do nothing; the specific device writer just wants no error to be raised (most basic form of simulation)

                
        raise SimulatedInstrumentError(2) #No match found, so invalid command and an error is raised.
    
    
    #see HSS simulated_read
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
        #output_buffer is extended with the data to be written (unless the buffer overflows based on the max_buffer_size, in which case an error is raised).
        if len(self.output_buffer)+len(data)>self.max_buffer_size:
            raise SimulatedInstrumentError(6,[self.max_buffer_size])
        else:
            self.output_buffer.extend(data)
        yield self.process_commands()
        

    @inlineCallbacks
    def process_commands(self):
        #split into a list of commands based on the universal serial input termination byte pattern ‘\r\n’, and the leftover bytes after the
        #last ‘\r\n’ remain in the output_buffer.
        *cmds, rest=self.output_buffer.split(self.dev.input_termination_byte)
        self.output_buffer=rest
        
        #For each command, the command is “interpreted” with the SerialCommunicationWrapper’s interpret_command method. If the interpretation
        #gives an error, we add it to the error_queue. If it gives a response, we extend the input_buffer with this response, ended with the
        #universal serial output termination byte pattern ‘\n’. Then, we continue to the next command (no matter what happened with the current one).
        for cmd in cmds:
            command_interpretation=None
            try:
                command_interpretation= yield deferToThread(lambda:self.interpret_serial_command(cmd))
                
            except SimulatedInstrumentError as e:
                self.error_list.append((str(dt.now()),cmd.decode(),str(e))) #see HSS for more on error list
                
            
            else:
                if command_interpretation:
                    command_interpretation=command_interpretation+self.dev.output_termination_byte
                    if len(self.input_buffer)+len(command_interpretation)>self.max_buffer_size:
                        raise SimulatedInstrumentError(6,[self.max_buffer_size]) #input buffer overflow
                self.input_buffer.extend(command_interpretation)
        
        
        
        
#communication wrapper for gpib devices
class SimulatedGPIBCommunicationInterface(SimulatedCommunicationInterface):
    
    
    #TODO: note: this assumes the chaining can be nested. this may not actually be true, i can't find any examples of nesting online. this is probably
    #overcomplicated... after writing this I found out there aren't usually more than 3 mnemonics.
    def expand_chained_commands(self,cmd):
        cmd=cmd.decode()
        keywords=cmd.split(':') #colon separates levels of tree
        tree=[keyword.split(';') for keyword in keywords] #semicolon separates mnemonics at that level of the tree
        full_msg=[]
        self.collect_paths(tree,[],full_msg) #fills full_msg with individual commands in DFS order
        return full_msg

    
    def collect_paths(self,tree,current_path,path_collector): #DFS on tree to get all paths from top to bottom
        if len(current_path)==len(tree):
            path_collector.append(bytearray(':'.join(current_path).encode()))
        else:
            for i in tree[len(current_path)]:
                self.collect_paths(tree,current_path+[i],path_collector)

    #GPIB command interpretation is more tricky than for serial commands because we have to check if the command fits into each structure in any way possible
    #until we find a match in the command_dict or run out of entries. An SCPI header structure that looks like “HELLo:THERe[:FRIEnd]” matches 24 possible
    #headers (the uppercase subset of each mnemonic denotes short form, the full case-insensitive mnemonic denotes long form, and the bracketed mnemonic is optional).
    #here, cmd is command from output buffer, and cmd_scpi_format is the key in the command dict representing a command structure.
    def check_if_scpi_match(self,cmd,cmd_scpi_format):
        
        pieces=cmd.split(b' ') #format is header + ' ' + list of args separated by commas, so this gives header and then string of args, or just header if no args
        body=pieces[0] #header
        args=None
        if len(pieces)>1:
            args=pieces[1]
        args_list=[]
        if args:
           args_list=args.split(b',') #if args, split by comma to get proper args list
        body_format,arg_nums=cmd_scpi_format
        body=body.decode()
        body_format=body_format.decode() #TODO: should be called header, and header structure instead of body and body format
        if body_format[0]==':':
           body_format=body_format[1:] #leading colon optional, was already removed from command if there
        if body[-1]=='?' and body_format[-1]=='?':
            body=body[:-1]
            body_format=body_format[:-1] #if both queries, remove question marks from each
        body_format=body_format.replace('[:',':[')#trick used to aid in detecting optional mnemonics. this will make it so when we split by colon, optional mnemonics will be in brackets.
        if type(arg_nums)==int:
            arg_nums=[arg_nums]
        if not (len(args_list) in arg_nums): #number of args used in command not supported by this command structure in the command_dict
            return False
        if not (body.lower()==body or body.upper()==body):  #check that each letter in the header has the same case: uppercase and lowercase cannot be mixed
            return False
        
        body=body.lower() #make command header lowercase
        body_chunks_list=body.split(':') #TODO: chunks -> mnemonics
        body_format_chunks_list=body_format.split(':')
        

        rem_block=[]
        rem_block_format=[]
        
                    
        index_in_format=0
        for body_chunk in body_chunks_list: #now comparing lists of mnemonics
            
            while True:
                #If we get to the end of the header structure and there are still more mnemonics in the command header,
                #it’s not a match.
                if index_in_format>=len(body_format_chunks_list):
                    return False
                body_format_chunk=body_format_chunks_list[index_in_format]
                can_skip=False
                if body_format_chunk[0]=='[' and body_format_chunk[-1]==']': #optional
                    can_skip=True
                    body_format_chunk=body_format_chunk[1:-1] #remove brackets
                prefix=''.join([char for char in body_format_chunk if char.isupper() or char.isnumeric()])
                prefix=prefix.lower() #get short form (lowercase letters removed) of header structure, then make it lowercase
                body_format_chunk=body_format_chunk.lower() #long form, but lowercase
                
                # if self.supports_any_prefix:
                #      if not (cmd_chunk.startswith(prefix) and cmd_format_chunk.startswith(cmd_chunk)):
                #        return False
                
                
                #If the command header mnemonic does not match the header structure mnemonic’s short form or long form it’s not a match-
                #unless the mnemonic was optional, in which case we skip to the next mnemonic in the header structure.
                if not (body_chunk==prefix or body_chunk==body_format_chunk):
                   if can_skip:
                       index_in_format=index_in_format+1
                   else:
                       return False
                else:
                   index_in_format=index_in_format+1
                   break
        #If we get to the end of the command header mnemonics and there are still more mnemonics in the header structure,
        #it’s not a match unless the rest of the mnemonics are optional.
        for rem_body_format_chunk in body_format_chunks_list[index_in_format:]:
            if body_format_chunk[0]!='[' or body_format_chunk[-1]!=']':
                    return False
        return True #Otherwise, if we get through each, and each mnemonic matches, it’s a match.


    def interpret_serial_command(self, cmd):
        #To interpret a GPIB command, the GPIBCommunicationWrapper first checks what type it is between default, set, and query.
        if not cmd:
            raise SimulatedInstrumentError(2)
            
        #2 default commands are supported: identification (*IDN?) and reset (*RST). These are taken care of in the wrapper since we don’t want the
        #user overwriting them. For the identification command we return the simulated_device’s id_string, and for the reset command we call its
        #set_default_settings method; each of these is written by users
        if cmd.decode()[0]=='*':
            if cmd==self.dev.id_command:
                if not self.dev.id_string:
                    raise SimulatedInstrumentError(7)
                return self.dev.id_string.encode()
            elif cmd==self.dev.clear_command:
                self.clear_buffers()
                return None
            elif cmd==self.dev.reset_command:
                self.dev.set_default_settings()
                return
            else:
                raise SimulatedInstrumentError(2)
                
         
        #For the other two types of commands, we check if the command meets one of the command structures in the device’s command_dict. If so, the
        #user-written generic device functionality (a method) that the user attached to that command structure when writing the command_dict will be
        #called, with the command’s arguments being passed to the method.
        else:
            is_query=False
            if cmd.split(b' ')[0].decode()[-1]=='?':
                is_query=True #question mark indicates query
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
                            raise SimulatedInstrumentError(3)
                    
                    else:
                        self.dev.execute_command(func,[arg.decode() for arg in args_list])
                        return
            raise SimulatedInstrumentError(2)
            
        
    #same as serial
    def read(self,count=None):
        resp=None
        if count:
            resp,rest=self.input_buffer[:count],self.input_buffer[count:]
            self.input_buffer=self.input_buffer[count:]
        else:
            resp=self.input_buffer
            self.input_buffer=bytearray(b'')
            
        return resp
        
    #TODO: do OOP better, move as much logic as possible to base class.
    
    #writing to a simulated GPIB device proves more complicated since it uses the SCPI standard, which provides more features to those writing to a device- features we needed to support for simulated devices to be
    #compatible with already-written experiment-supporting code. An SCPI command consists of a header followed by arguments. The set of commands that a device
    #supports can be thought of a wide, but shallow, tree of what are called mnemonics, which are each alphanumeric bytestrings. Any traversal from the root
    #node to a leaf, each separated by a colon, constitutes a valid header. This seems simple enough, but to simplify things for the user there are a lot of
    #tricks they can use when writing commands. First, each mnemonic in the header has a short form and a long form, and either form can be used for each mnemonic.
    #Second, some mnemonics are optional. Finally, multiple individual commands can be chained into one big compound command, with an option to avoid redundancy
    #when consecutive commands follow the same path in the header tree up to some point (have a shared prefix of some amount of mnemonics). To add a new command
    #to the chain restarting from the root node in the tree, one separates by ‘:;’. To chain consecutive commands whose headers are the same up to some point, one
    #writes the shared path (with mnemonics separated by colons), puts a colon, and then writes the remaining header path and arguments for each command,
    #with each “command remainder” being separated by a semicolon. Finally, commands are either default commands, set commands, or query commands, and each has
    #slightly different behavior. Our implementation supports all these features. The Programmer’s Manual for a GPIB Device will cover each valid
    #command header structure, where a command header structure is a bytestring written in a specific format that shows all the valid ways the command header
    #can be written. We want to make it so the valid command header structures (which each encode many possible valid ways to write the same valid command)
    #can simply be written in the command_dict of a simulated specific GPIB device exactly as appears in the Programmer’s Manual and attached to generic device
    #methods, just like a serial command can for a simulated serial device, and labs can be confident any command that was written to the real device
    #in their experiment-supporting code will still work in the same way with the simulated device, no matter what type of chaining or approach to writing each individual mnemonic in the header was used.
    @inlineCallbacks
    def write(self,data):
        
        if data[:1].decode()==':':
            data=data[1:] #leading colon to represent root optional
        #puts the data in the output_buffer (unless this will cause buffer overflow; then there’s an error).
        if len(self.output_buffer)+len(data)>self.max_buffer_size:
            raise SimulatedInstrumentError(6,[self.max_buffer_size])
        else:
            self.output_buffer.extend(data)
        yield self.process_commands()
            
        
    @inlineCallbacks
    def process_commands(self):
        self.input_buffer=bytearray(b'')
        
        #splits the buffer into a Python list by ‘;:’, with each element in the list
        #being an individual command- except for those that used the shared-path trick (as these represent multiple commands)
        chained_cmds =self.output_buffer.split(self.dev.input_termination_byte)
        
        self.output_buffer=bytearray(b'') #reset input and output buffers after parsing bytes in output buffer(this is just how GPIB communication works- before a new write occurs both buffers are cleared).
        expanded_commands=[]
        
        #For each element in our list, we check if it is still a compound command due to the shared-path trick and expand it if so using DFS, and by doing
        #so form a new list of all individual commands with full headers, preserving the order (as if the writer had chained by resetting to the root
        #node each time and not used the trick)
        for chained_cmd in chained_cmds:
            expanded_commands.extend(self.expand_chained_commands(chained_cmd))
            
            
        for cmd in expanded_commands:
            command_interpretation=None
            try:
                command_interpretation= yield deferToThread(lambda:self.interpret_serial_command(cmd))

            except SimulatedInstrumentError as e:
                
                self.error_list.append((str(dt.now()),cmd.decode(),str(e)))
                #TODO: If interpreting a command gives an error, unlike in the serial case, after we add the error to the error_queue all commands after are ignored,
                #the device output so far is erased from the input_buffer, and the write has ended. So This needs to be changed.
            
            else:
                if command_interpretation:
                    if len(self.input_buffer)+len(command_interpretation)>self.max_buffer_size:
                        raise SimulatedInstrumentError(6,[self.max_buffer_size])
                        
                    #each returned response from an interpretation is added to the input_buffer, with a semicolon as the device’s output termination character.
                    self.input_buffer.extend(command_interpretation+self.dev.output_termination_byte)
                    
                
        
        if self.input_buffer:
            self.input_buffer=self.input_buffer[:-1] #get ride of last semicolon
            self.input_buffer.extend(b'\n')
            #The GPIB Bus Server will view the real termination character as ‘\n’, and view all the query responses separated by ‘;’ as one big device response,
            #so we add this to the end of the wrapper’s input_buffer once all commands have been interpreted and the full response has been put into the input_buffer.


                
            
