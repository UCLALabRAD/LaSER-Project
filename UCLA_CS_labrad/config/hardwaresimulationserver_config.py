#config file HSS uses to find simulated device classes to import
class config(object):
     sim_instr_models = [('UCLA_CS_labrad.servers.functiongenerators.Agilent33210A','SimulatedAgilent33210A'),('UCLA_CS_labrad.servers.AMOboxes.AMO3_server','SimulatedAMO3'),('UCLA_CS_labrad.servers.oscilloscopes.KeysightDSOX2024A','SimulatedKeysightDSOX2024A')]
#list of tuples of form (module, name of specific device class in module)
