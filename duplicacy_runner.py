#!/usr/bin/env python3

import argparse
import json
import logging
from pathlib import Path
import subprocess as sub
import time

from log_parser import LogParser
from update_handler import UpdateHandler

# TODO:
#   - only stop containers if logfile not present
#   - log duplicacy output to file
#     - log duplicacy_runner output to same file
#     - format it not stupidly
#   - file lock to prevent multiple of same backup running
#   - home assistant auto detection bs
#   - replace existing scripts/scheduled jobs

def get_backup_name(backup_dir):
    preferences_filename = args.backup_dir/'.duplicacy'/'preferences'
    with open(preferences_filename, 'r') as f:
        name = json.load(f).get('id')
        if not name:
            raise ValueError(f'No "id" found in {preferences_filename}')
    return name

def run_backup(log_parser, backup_dir, logfile):
    cmd = ['cat', logfile] if logfile else ['duplicacy', '-log', 'backup', '-stats']
    logging.info(f'Starting Backup using cmd: {cmd}')
    
    proc = sub.Popen(cmd, cwd=backup_dir, stdout=sub.PIPE, stderr=sub.STDOUT, text=True)

    while True:
        line = proc.stdout.readline()
        if not line:
            ret = proc.poll()
            if ret is not None:
                log_parser.handle_return_code(ret)
                break
            time.sleep(0.1)
            continue

        log_parser.parse_line(line)
        logging.info(line)

    logging.info(f'Backup finished with return code {ret}')

def docker_command(containers, command):
    for container in containers:
        sub.run(['docker', command, container])

def run(args):
    name = args.backup_name if args.backup_name else get_backup_name(args.backup_dir)
    log_parser = LogParser(UpdateHandler(args.configfile, name))

    logging.info(f'Stopping containers: {args.containers}')
    docker_command(args.containers, 'stop')
    try:
        run_backup(log_parser, args.backup_dir, args.logfile)
    finally:
        logging.info(f'Restarting containers: {args.containers}')
        docker_command(args.containers, 'start')
    
        
def main():
    parser = argparse.ArgumentParser(
        prog='DuplicacyRunner',
        description='Script to run duplicacy commands and output status/stats to MQTT'
    )
    parser.add_argument('-d', '--backup-dir', required=True, help='Path to the backup directory')
    parser.add_argument('-n', '--backup-name', help='Name of backup. Optional, will use id from duplicacy preferences file if not provided')
    parser.add_argument('-l', '--logfile', help='Parse logfile instead of running. Used for testing.')
    parser.add_argument('-c', '--containers', nargs='*', help='Docker containers to stop before backup')
    parser.add_argument('--configfile', default=str(Path.home()/'.config'/'duplicacy_runner'/'config.json'), help='Configfile location')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d: %(message)s",
    )

    logging.info('======')
    logging.info('Arguments: %s', json.dumps(vars(args), indent=2, ensure_ascii=False))
    logging.info('======')

    run(args)


if __name__ == "__main__":
    main()
