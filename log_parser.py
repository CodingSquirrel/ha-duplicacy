from datetime import datetime, timedelta, timezone
import re

from state_types import ProgressState, CompletionState
from utils import convert_size

class LogParser:
    line_re = re.compile('(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) (?P<level>\S+) (?P<type>\S+) (?P<message>.*)')
    revision_re = re.compile('Backup for .+ at revision (?P<revision>\d+) completed')
    files_re = re.compile('Files: (?P<files>\d+[\d.,]*\d*) total, (?P<size>\d+[\d.,]*\d*)(?P<size_unit>[TGMK]?) bytes; (?P<new_files>\d+[\d.,]*\d*) new, (?P<new_size>\d+[\d.,]*\d*)(?P<new_size_unit>[TGMK]?) bytes')
    chunks_re = re.compile('All chunks: (?P<chunks>\d+[\d.,]*\d*) total, (?P<size>\d+[\d.,]*\d*)(?P<size_unit>[TGMK]?) bytes; (?P<new_chunks>\d+[\d.,]*\d*) new, (?P<new_size>\d+[\d.,]*\d*)(?P<new_size_unit>[TGMK]?) bytes')
    time_re = re.compile('Total running time: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})')
    progress_re = re.compile('(?:Uploaded|Skipped) chunk \d+ size \d+, (?P<speed>\d+[\d.,]*\d*)(?P<unit>[TGMK]?)B/s (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2}) (?P<percent>\d+[\d.,]*\d*)%')

    def __init__(self, update_handler):
        self.update_handler = update_handler
        self.completion_state = CompletionState()
        self.last_publish_progress = datetime.fromtimestamp(0, timezone.utc).astimezone()

    def parse_line(self, line):
        match = self.line_re.match(line)

        if not match:
            return

        ts = datetime.fromisoformat(match['datetime']).astimezone()
        if match['level'] == 'WARN':
            self.completion_state.warnings.append(line)
        elif match['level'] == 'ERROR':
            self.completion_state.errors.append(line)
            return
        elif match['type'] == 'BACKUP_START':
            self.completion_state.time_started = ts
            progress = ProgressState(0.0, timedelta(), timedelta(), 0.0)
            self.update_handler.send_progress(progress)
        elif match['type'] == 'BACKUP_END':
            self.completion_state.time_finished = ts
            progress = ProgressState(0.0, timedelta(), timedelta(), 0.0, False)
            self.update_handler.send_progress(progress)
            self.parse_backup_end(match['message'])
        elif match['type'] == 'BACKUP_STATS':
            self.parse_backup_stats(match['message'])
        elif match['type'] == 'UPLOAD_PROGRESS':
            self.parse_upload_progress(match['message'], ts)

    def handle_return_code(self, return_code):
        if return_code != 0:
            self.completion_state.errors.append(f'Non-zero return code: {return_code}')
        self.update_handler.send_completion(self.completion_state)
        # Redundant reset of progress. In case underlying command crashes without signalling end
        progress = ProgressState(0.0, timedelta(), timedelta(), 0.0, False)
        self.update_handler.send_progress(progress)

    def match(self, compiled_re, line):
        match = compiled_re.match(line)
        if not match:
            self.completion_state.errors.append(f'Failed to parse "{line}"')
        return match

    def parse_backup_end(self, line):
        match = self.match(self.revision_re, line)

        self.completion_state.revision = int(match['revision'])

    def parse_backup_stats(self, line):
        if line.startswith('Files:'):
            match = self.match(self.files_re, line)
            
            self.completion_state.files = int(match['files'])
            files_size = convert_size(match['size'], match['size_unit'], 'G')
            self.completion_state.files_size = files_size
            self.completion_state.new_files = int(match['new_files'])
            new_files_size = convert_size(match['new_size'], match['new_size_unit'], 'G')
            self.completion_state.new_files_size = new_files_size
        elif line.startswith('All chunks:'):
            match = self.match(self.chunks_re, line)
            
            self.completion_state.chunks = int(match['chunks'])
            chunks_size = convert_size(match['size'], match['size_unit'], 'G')
            self.completion_state.chunks_size = chunks_size
            self.completion_state.new_chunks = int(match['new_chunks'])
            new_chunks_size = convert_size(match['new_size'], match['new_size_unit'], 'G')
            self.completion_state.new_chunks_size = new_chunks_size
        elif line.startswith('Total running time:'):
            match = self.match(self.time_re, line)

            time_elapsed = timedelta(hours=int(match['hour']), minutes=int(match['min']), seconds=int(match['sec']))
            self.completion_state.time_elapsed = time_elapsed

    def parse_upload_progress(self, line, ts):
        match = self.match(self.progress_re, line)
        if not match:
            self.completion_state.errors.append(f'Failed to parse "{line}"')
            return

        progress = ProgressState(
            match['percent'],
            timedelta(hours=int(match['hour']), minutes=int(match['min']), seconds=int(match['sec'])),
            ts - self.completion_state.time_started,
            convert_size(match['speed'], match['unit'], 'M')
        )

        if (ts - self.last_publish_progress).total_seconds() >= 1:
            self.last_publish_progress = ts
            self.update_handler.send_progress(progress)
