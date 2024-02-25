from contextlib import contextmanager
from datetime import datetime
import json
import logging
from pathlib import Path
import subprocess as sub
import sys

logger = logging.getLogger(__name__)
    
@contextmanager
def file_lock(lock_dir):
    path = lock_dir/'LOCK'
    try:
        open(path, 'x').close()
    except FileExistsError:
        logger.info('Backup already running, quitting')
        sys.exit(0)
    try:
        yield
    finally:
        path.unlink()

def convert_size(size, from_unit, to_unit):
    UNITS = {'': 1, 'K': 2 ** 10, 'M': 2 ** 20, 'G': 2 ** 30, 'T': 2 ** 40}
    return float(size.replace(',','')) * UNITS[from_unit] / UNITS[to_unit]

def get_backup_name(backup_dir):
    preferences_filename = Path(backup_dir)/'.duplicacy'/'preferences'
    with open(preferences_filename, 'r') as f:
        name = json.load(f)[0].get('id')
        if not name:
            raise ValueError(f'No "id" found in {preferences_filename}')
    return name

def docker_command(containers, command, dry_run):
    if not dry_run:
        for container in containers:
            sub.run(['docker', command, container])

def get_log_handlers(log_dir, backup_name):
    class DispatchingFormatter:
        def __init__(self, formatters, default_formatter):
            self._formatters = formatters
            self._default_formatter = default_formatter

        def format(self, record):
            formatter = self._formatters.get(record.name, self._default_formatter)
            return formatter.format(record)
        
    handlers=[logging.StreamHandler(sys.stdout)]
    
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = log_dir/f'{backup_name}_backup_{datetime.now().strftime("%Y-%m-%d-%H-%M")}.log'
    
    handlers.append(logging.FileHandler(logfile, mode='a'))
    
    formatter = DispatchingFormatter(
        {'DIRECT_LOGGER': logging.Formatter('%(message)s')},
        logging.Formatter('%(asctime)s %(levelname)s %(filename)s:%(lineno)d: %(message)s')
    )
    for handler in handlers:
        handler.setFormatter(formatter)

    return handlers, logfile
