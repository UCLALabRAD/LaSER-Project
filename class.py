
def self.fill_buffer(msg):
	if msg[0]==':'
	    msg=msg[1:]
	cmds=msg.split(";:")
	for cmd in cmds:
        keywords=cmd.split(':')
        paths=[keyword.split(';') for keyword in keywords]



def expand_node(paths,current_path)
	if len(current_path)=len(paths):
		#add current path to buffer
	else:
		for i in paths[len(current_path)]:
			expand_node(current_path+[i])




cmd=None
		args=[]
		temp= sub_cmd_w_args.split(' ')
		if len(temp)>2:
			Error
		else:
			cmd=temp[0]
			if len(temp)==2:
                args.extend(temp[1].split(','))

def check_if_scpi_match(self,cmd,cmd_scpi_format):
        cmd,args_list=cmd.split(' ')
        args=args_list.split(',')
        cmd_format,arg_nums=cmd_format
        if not (len(args) in num_args):
            return False
        if (cmd[-1]=='?' and cmd_format_chunk[-1]=='?'):
            cmd=cmd[:-1]
            cmd_format_chunk=cmd_format_chunk[:-1]
        elif (cmd[-1]!='?' and cmd_format_chunk[-1]!='?'):
        	pass
        else:
        	return False
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
          #  if self.supports_any_prefix:
          #      if not (cmd_chunk.startswith(prefix) and cmd_format_chunk.startswith(cmd_chunk)):
           #        return False
            if not (cmd_chunk==prefix or cmd_chunk==cmd_format_chunk):
               return False
        return True







    
    

    

        











class SimulatedInConn
