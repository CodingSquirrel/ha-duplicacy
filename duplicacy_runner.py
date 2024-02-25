#!/usr/bin/env python3

import argparse
import json
import logging
from pathlib import Path
import subprocess as sub
import time

from log_parser import LogParser
from update_handler import UpdateHandler
from utils import (
    file_lock,
    get_backup_name,
    docker_command,
    get_log_handlers
)


logger = logging.getLogger(__name__)
direct_logger = logging.getLogger('DIRECT_LOGGER')

def run_backup(log_parser, backup_dir, dry_run, backup_args):
    cmd = ['duplicacy', '-log', 'backup', '-stats']
    if dry_run:
        cmd.append('-dry-run')
    if backup_args:
        cmd.extend(backup_args)
    logger.info(f'Starting Backup using cmd: {cmd}')
    
    proc = sub.Popen(cmd, cwd=backup_dir, stdout=sub.PIPE, stderr=sub.STDOUT, encoding='utf-8', errors='backslashreplace', text=True)

    while True:
        line = proc.stdout.readline().rstrip()
        if not line:
            ret = proc.poll()
            if ret is not None:
                log_parser.handle_return_code(ret)
                break
            time.sleep(0.1)
            continue

        log_parser.parse_line(line)
        direct_logger.info(line)

    logger.info(f'Backup finished with return code {ret}')

def run(args):
    with file_lock(Path(args.backup_dir)/'.duplicacy'):
        log_parser = LogParser(UpdateHandler(args.mqtt_hostname, args.mqtt_port, args.mqtt_username, args.mqtt_password, args.discovery_root, args.backup_name))

        try:
            logger.info(f'Stopping containers: {args.containers}')
            docker_command(args.containers, 'stop', args.dry_run)
            run_backup(log_parser, args.backup_dir, args.dry_run, args.backup_args)
        except Exception as e:
            logging.exception('Uncaught exception raised during main execution')
            raise e from None
        finally:
            logger.info(f'Restarting containers: {args.containers}')
            docker_command(args.containers, 'start', args.dry_run)

def parse_args():
    parser = argparse.ArgumentParser(
        prog='DuplicacyRunner',
        description='Script to run duplicacy commands and output status/stats to MQTT'
    )
    parser.add_argument('-d', '--backup-dir', required=True, help='Path to the backup directory')
    parser.add_argument('-n', '--backup-name', help='Name of backup. Optional, will use id from duplicacy preferences file if not provided')
    parser.add_argument('-l', '--log-dir', help='Directory where to store logfiles')
    parser.add_argument('-c', '--containers', nargs='*', help='Docker containers to stop before backup')
    parser.add_argument('-r', '--discovery-root', help='Root discovery topic path for Home Assistant')
    parser.add_argument('--mqtt-hostname', help='Hostname of MQTT broker')
    parser.add_argument('--mqtt-port', help='Port of MQTT broker')
    parser.add_argument('--mqtt-username', help='Username to login to MQTT broker')
    parser.add_argument('--mqtt-password', help='Password to login to MQTT broker')
    parser.add_argument('--configfile', default=str(Path.home()/'.config'/'duplicacy_runner'/'config.json'), help='Configfile location')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('backup_args', nargs='*')

    args = parser.parse_args()

    defaults = {
        'backup_name': get_backup_name(args.backup_dir),
        'log_dir': str(Path(args.backup_dir)/'.duplicacy'/'logs'),
        'containers': [],
        'discovery_root': 'homeassistant',
        'mqtt_hostname': None,
        'mqtt_port': 1883,
        'mqtt_username': None,
        'mqtt_password': None,
    }
    config = {}
    if Path(args.configfile).is_file():
        with open(args.configfile, 'r') as f:
            config = json.load(f)
    args_dict = {k: v for k, v in vars(args).items() if v is not None}
    
    return argparse.Namespace(**{**defaults, **config, **args_dict})
        
def main():
    args = parse_args()

    handlers, logfile = get_log_handlers(args.log_dir, args.backup_name)
    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers
    )

    logger.info('Logging to: %s', logfile)
    logger.info('======')
    logger.info('Arguments: %s', json.dumps({**vars(args), 'mqtt_password': '***'}, indent=2, ensure_ascii=False))
    logger.info('======')

    run(args)


if __name__ == "__main__":
    main()
