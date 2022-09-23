import io
import os
import sys

from configparser import ConfigParser


class SimGPIBDeviceConfig(object):
    def __init__(self, name, description, version, path, filename):
        self.name = name
        self.description = description
        self.version = version
        self.version_tuple = version_tuple(version)
        self.module_path=os.path.join(path,filename)
        self.module_name=filename[:-3]
        self.filename=filename
		



def from_string(conf, filename=None, path=None):
    """Parse a ServerConfig object from a node config string."""
    if isinstance(conf, bytes):
        conf = conf.decode('utf-8')
    scp = ConfigParser()
    scp.readfp(io.StringIO(conf))

    # general information
    name = scp.get('info', 'name', raw=True)
    description = scp.get('info', 'description', raw=True)
    if scp.has_option('info', 'version'):
        version = scp.get('info', 'version', raw=True)
    else:
        version = '0.0'

    return SimDeviceConfig(name, description, version,
                        path, filename)


def find_config_block(path, filename):
    """Find a Node configuration block embedded in a file."""
    # markers to delimit node info block
    BEGIN = b"### BEGIN SIMULATED GPIB DEVICE INFO"
    END = b"### END SIMULATED GPIB DEVICE INFO"
    with open(os.path.join(path, filename), 'rb') as file:
        foundBeginning = False
        lines = []
        for line in file:
            if line.upper().strip().startswith(BEGIN):
                foundBeginning = True
            elif line.upper().strip().startswith(END):
                break
            elif foundBeginning:
                line = line.replace(b'\r', b'')
                line = line.replace(b'\n', b'')
                lines.append(line)
        return b'\n'.join(lines) if lines else None


def version_tuple(version):
    """Get a tuple from a version string that can be used for comparison.
    Version strings are typically of the form A.B.C-X where A, B and C
    are numbers, and X is extra text denoting dev status (e.g. alpha or beta).
    Given this structure, we cannot just use string comparison to get the order
    of versions; instead we parse the version into a tuple
    ((int(A), int(B), int(C)), version)
    If we cannot parse the numeric part, we just use the empty tuple for the
    first entry, and for such tuples the comparison will just fall back to
    alphabetic comparison on the full version string.
    """
    numstr, _, _extra = version.partition('-')
    try:
        nums = tuple(int(n) for n in numstr.split('.'))
    except Exception:
        nums = ()
    return (nums, version)