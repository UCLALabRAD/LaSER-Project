"""
Script Scanner config object.
Specifies the scripts available to script scanner on startup.
"""

class config(object):

    # list in the format (import_path, class_name)
    scripts = []

    allowed_concurrent = {
    }
    
    launch_history = 1000
