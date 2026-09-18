from datetime import datetime, timedelta
import logging
import pytest
from unittest import mock

from log_parser import LogParser, LogParseException
from state_types import CompletionState, ProgressState

logger = logging.getLogger(__name__)

def test_parse_line_warn():
    mock_handler = mock.Mock()
    parser = LogParser(mock_handler)

    line = "2024-09-06 13:10:42.331 WARN SFTP_RETRY Encountered an error (failed to send packet: EOF); retry after 1 second(s)"
    expected_completion = CompletionState()
    expected_completion.warnings = [line]

    parser.parse_line(line)
    mock_handler.send_completion.assert_not_called()
    mock_handler.send_progress.assert_not_called()
    assert parser.completion_state == expected_completion

def test_parse_line_error():
    mock_handler = mock.Mock()
    parser = LogParser(mock_handler)

    line = "2024-03-19 09:55:01.228 ERROR VSS_SNAPSHOT Shadow copy creation failed: DoSnapshotSet didn't finish properly"
    expected_completion = CompletionState()
    expected_completion.errors = [line]

    parser.parse_line(line)
    mock_handler.send_completion.assert_not_called()
    mock_handler.send_progress.assert_not_called()
    assert parser.completion_state == expected_completion

def test_parse_line_start():
    mock_handler = mock.Mock()
    parser = LogParser(mock_handler)

    line = "2024-09-06 12:10:12.941 INFO BACKUP_START Last backup at revision 193 found"
    ts = datetime.fromisoformat("2024-09-06 12:10:12.941").astimezone()
    expected_completion = CompletionState(time_started=ts)
    expected_progress = ProgressState(0.0, timedelta(), timedelta(), 0.0)

    parser.parse_line(line)
    mock_handler.send_completion.assert_not_called()
    mock_handler.send_progress.assert_called_once_with(expected_progress)
    assert parser.completion_state == expected_completion

def test_parse_line_end():
    mock_handler = mock.Mock()
    parser = LogParser(mock_handler)

    line = "2024-09-06 19:22:57.534 INFO BACKUP_END Backup for C:\\ at revision 194 completed"
    ts = datetime.fromisoformat("2024-09-06 19:22:57.534").astimezone()
    expected_completion = CompletionState(time_finished=ts, revision=194)
    expected_progress = ProgressState(0.0, timedelta(), timedelta(), 0.0, False)

    parser.parse_line(line)
    mock_handler.send_completion.assert_not_called()
    mock_handler.send_progress.assert_called_once_with(expected_progress)
    assert parser.completion_state == expected_completion

def test_parse_line_end_error():
    mock_handler = mock.Mock()
    parser = LogParser(mock_handler)

    line = "2024-09-06 19:22:57.534 INFO BACKUP_END Backup for C:\\ at revision completed"
    ts = datetime.fromisoformat("2024-09-06 19:22:57.534").astimezone()
    expected_completion = CompletionState(time_finished=ts)
    expected_completion.errors = [f'Failed to parse "{line}"']
    expected_progress = ProgressState(0.0, timedelta(), timedelta(), 0.0, False)

    with pytest.raises(LogParseException):
        parser.parse_line(line)
    mock_handler.send_completion.assert_not_called()
    mock_handler.send_progress.assert_called_once_with(expected_progress)
    assert parser.completion_state == expected_completion

@pytest.mark.parametrize(
        "line, expected_completion",
        [
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS Files: 5780 total, 6,424 bytes; 5780 new, 641,8 bytes",
                CompletionState(files=5780, files_size=pytest.approx(5.982816219329834e-06), new_files=5780, new_files_size=pytest.approx(5.977228283882141e-06))
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS Files: 1 total, 64,24K bytes; 1 new, 6,418K bytes",
                CompletionState(files=1, files_size=pytest.approx(0.00612640380859375), new_files=1, new_files_size=pytest.approx(0.0061206817626953125))
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS Files: 2 total, 642,4M bytes; 99999 new, 64,18M bytes",
                CompletionState(files=2, files_size=pytest.approx(6.2734375), new_files=99999, new_files_size=pytest.approx(6.267578125))
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS Files: 99999 total, 6424G bytes; 1 new, 6418G bytes",
                CompletionState(files=99999, files_size=6424, new_files=1, new_files_size=6418)
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS Files: 19153 total, 5,633G bytes; 12 new, -12G bytes",
                CompletionState(files=19153, files_size=5633, new_files=12, new_files_size=-12)
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS All chunks: 1340055 total, 64,24 bytes; 1338843 new, 6,418 bytes, 6385 bytes uploaded",
                CompletionState(chunks=1340055, chunks_size=pytest.approx(5.982816219329834e-06), new_chunks=1338843, new_chunks_size=pytest.approx(5.977228283882141e-06))
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS All chunks: 1 total, 642,4K bytes; 1 new, 64,18K bytes, 6385K bytes uploaded",
                CompletionState(chunks=1, chunks_size=pytest.approx(0.00612640380859375), new_chunks=1, new_chunks_size=pytest.approx(0.0061206817626953125))
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS All chunks: 2 total, 6,424M bytes; 9999 new, 641,8M bytes, 6385M bytes uploaded",
                CompletionState(chunks=2, chunks_size=pytest.approx(6.2734375), new_chunks=9999, new_chunks_size=pytest.approx(6.267578125))
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS All chunks: 9999 total, 6424G bytes; 1 new, 6418G bytes, 6385G bytes uploaded",
                CompletionState(chunks=9999, chunks_size=6424, new_chunks=1, new_chunks_size=6418)
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS Total running time: 07:12:45",
                CompletionState(time_elapsed=timedelta(hours=7, minutes=12, seconds=45))
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS Total running time: 4 days 00:00:00",
                CompletionState(time_elapsed=timedelta(days=4))
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS Total running time: 1 day 01:00:01",
                CompletionState(time_elapsed=timedelta(days=1, hours=1, seconds=1))
            ),
            (
                "2024-09-06 19:22:57.534 INFO BACKUP_STATS asdf",
                CompletionState()
            ),
        ]
)
def test_parse_line_stats(line, expected_completion):
    mock_handler = mock.Mock()
    parser = LogParser(mock_handler)

    parser.parse_line(line)
    mock_handler.send_completion.assert_not_called()
    mock_handler.send_progress.assert_not_called()
    assert parser.completion_state == expected_completion

@pytest.mark.parametrize(
        "line",
        [
            "2024-09-06 19:22:57.534 INFO BACKUP_STATS Files: 5780 toal, 6,424 bytes; 5780 new, 641,8 bytes",
            "2024-09-06 19:22:57.534 INFO BACKUP_STATS All chunks: 1340055 total, 64,24bytes; 1338843 new, 6,418 bytes, 6385 bytes uploaded",
            "2024-09-06 19:22:57.534 INFO BACKUP_STATS Total running time: asdf",
        ]
)
def test_parse_line_stats_error(line):
    mock_handler = mock.Mock()
    parser = LogParser(mock_handler)

    expected_completion = CompletionState()
    expected_completion.errors = [f'Failed to parse "{line}"']

    with pytest.raises(LogParseException):
        parser.parse_line(line)
    mock_handler.send_completion.assert_not_called()
    mock_handler.send_progress.assert_not_called()
    assert parser.completion_state == expected_completion

@pytest.mark.parametrize(
        "line, expected_progress",
        [
            (
                "2024-09-06 19:22:57.534 INFO UPLOAD_PROGRESS Uploaded chunk 0 size 4914586, 4.69B/s 00:25:30 0.0%",
                ProgressState('0.0', timedelta(minutes=25, seconds=30), timedelta(), upload_speed=pytest.approx(4.472732543945313e-06))
            ),
            (
                "2024-09-06 19:22:57.534 INFO UPLOAD_PROGRESS Skipped chunk 200 size 1, 4.69KB/s 12:00:25 0.9%",
                ProgressState('0.9', timedelta(hours=12, seconds=25), timedelta(), upload_speed=pytest.approx(0.004580078125))
            ),
            (
                "2024-09-06 19:22:57.534 INFO UPLOAD_PROGRESS Uploaded chunk 9999 size 10, 4.69MB/s 1 day 00:25:30 30.1%",
                ProgressState('30.1', timedelta(days=1, minutes=25, seconds=30), timedelta(), upload_speed=pytest.approx(4.69))
            ),
            (
                "2024-09-06 19:22:57.534 INFO UPLOAD_PROGRESS Skipped chunk 0 size 9999, 4.69GB/s 2 days 00:00:00 100.0%",
                ProgressState('100.0', timedelta(days=2), timedelta(), upload_speed=pytest.approx(4802.56))
            ),
            (
                "2024-09-06 19:22:57.534 INFO UPLOAD_PROGRESS Skipped chunk 0 size 9999, 4.69GB/s n/a 101.6%",
                ProgressState('101.6', timedelta(), timedelta(), upload_speed=pytest.approx(4802.56))
            ),
        ]
)
def test_parse_line_progress(line, expected_progress):
    mock_handler = mock.Mock()
    parser = LogParser(mock_handler)

    parser.completion_state.time_started = datetime.fromisoformat("2024-09-06 18:19:54.534").astimezone()
    expected_progress.time_elapsed = timedelta(hours=1, minutes=3, seconds=3)

    parser.parse_line(line)
    mock_handler.send_completion.assert_not_called()
    mock_handler.send_progress.assert_called_once_with(expected_progress)

def test_parse_line_progress_error():
    mock_handler = mock.Mock()
    parser = LogParser(mock_handler)
    
    line = "2024-09-06 19:22:57.534 INFO UPLOAD_PROGRESS Uploaded chunk 0 siz 4914586, 4.69B/s 00:25:30 0.0%"
    expected_completion = CompletionState()
    expected_completion.errors = [f'Failed to parse "{line}"']

    with pytest.raises(LogParseException):
        parser.parse_line(line)
    mock_handler.send_completion.assert_not_called()
    mock_handler.send_progress.assert_not_called()
    assert parser.completion_state == expected_completion
