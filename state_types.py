from dataclasses import dataclass, field, fields, asdict, InitVar
from datetime import datetime, timedelta, timezone
import json
from typing import Literal, Any

@dataclass
class ProgressState:
    percent: int = field(metadata={
        'icon': 'mdi:progress-upload',
        'name': 'Percent',
        'state_class': 'measurement',
        'unit_of_measurement': '%',
    })
    time_remaining: timedelta = field(metadata={
        'device_class': 'duration',
        'name': 'Time Remaining',
        'state_class': 'measurement',
        'unit_of_measurement': 's',
    })
    time_elapsed: timedelta = field(metadata={
        'device_class': 'duration',
        'name': 'Time Elapsed',
        'state_class': 'measurement',
        'unit_of_measurement': 's',
    })
    upload_speed: int = field(metadata={
        'device_class': 'data_rate',
        'name': 'Upload Speed',
        'suggested_display_precision': 2,
        'state_class': 'measurement',
        'unit_of_measurement': 'MB/s',
    })
    running: bool = field(default=True, metadata={
        'device_class': 'running',
        'name': 'Running',
    })

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            'time_remaining': self.time_remaining.total_seconds(),
            'time_elapsed': int(self.time_elapsed.total_seconds()),
            'running': 'ON' if self.running else 'OFF'
        }

    @classmethod
    def fields_discovery(cls, host, name, state_topic, root) -> dict[str, Any]:
        device_id = f'duplicacy_{host}_{name}_progress'
        return {
            f'{root}/{"binary_sensor" if field.type is bool else "sensor"}/{device_id}/{field.name}/config': {
                'device': {
                    'identifiers': [device_id],
                    'name': f'{host}/{name} Backup Progress'
                },
                'entity_category': 'diagnostic',
                'object_id': f'{device_id}_{field.name}',
                'state_topic': state_topic,
                'unique_id': f'{device_id}_{field.name}',
                'value_template': f'{{{{ value_json.{field.name} }}}}',
                **field.metadata
            }
            for field in fields(cls)
        }
            

@dataclass
class CompletionState:
    revision: int = field(default=0, metadata={
        'icon': 'mdi:counter',
        'name': 'Revision',
        'state_class': 'measurement',
    })
    time_started: datetime = field(default=datetime.fromtimestamp(0, timezone.utc), metadata={
        'device_class': 'timestamp',
        'name': 'Time Started',
    })
    time_finished: datetime = field(default=datetime.fromtimestamp(0, timezone.utc), metadata={
        'device_class': 'timestamp',
        'name': 'Time Finished',
    })
    time_elapsed: timedelta = field(default=timedelta(), metadata={
        'device_class': 'duration',
        'name': 'Time Elapsed',
        'state_class': 'measurement',
        'unit_of_measurement': 's',
    })
    files: int = field(default=0, metadata={
        'icon': 'mdi:file-cloud',
        'name': 'Files',
        'state_class': 'measurement',
    })
    files_size: int = field(default=0, metadata={
        'device_class': 'data_size',
        'name': 'Files Size',
        'suggested_display_precision': 2,
        'state_class': 'measurement',
        'unit_of_measurement': 'GiB',
    })
    new_files: int = field(default=0, metadata={
        'icon': 'mdi:file-upload',
        'name': 'New Files',
        'state_class': 'measurement',
    })
    new_files_size: int = field(default=0, metadata={
        'device_class': 'data_size',
        'name': 'New Files Size',
        'suggested_display_precision': 2,
        'state_class': 'measurement',
        'unit_of_measurement': 'GiB',
    })
    chunks: int = field(default=0, metadata={
        'icon': 'mdi:database',
        'name': 'Chunks',
        'state_class': 'measurement',
    })
    chunks_size: int = field(default=0, metadata={
        'device_class': 'data_size',
        'name': 'Chunks Size',
        'suggested_display_precision': 2,
        'state_class': 'measurement',
        'unit_of_measurement': 'GiB',
    })
    new_chunks: int = field(default=0, metadata={
        'icon': 'mdi:database-arrow-up',
        'name': 'New Chunks',
        'state_class': 'measurement',
    })
    new_chunks_size: int = field(default=0, metadata={
        'device_class': 'data_size',
        'name': 'New Chunks Size',
        'suggested_display_precision': 2,
        'state_class': 'measurement',
        'unit_of_measurement': 'GiB',
    })
    state: str = field(default='', metadata={
        'icon': 'mdi:cloud-check-variant',
        'name': 'State',
        'device_class': 'enum',
        'json_attributes_template': '{ "warnings": {{ value_json.warnings }}, "errors": {{ value_json.errors }} }'
    })

    def __post_init__(self):
        self.warnings = []
        self.errors = []

    @property
    def state_value(self) -> str:
        if self.errors:
            return 'error'
        if self.warnings:
            return 'warning'
        return 'success'

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            'time_started': self.time_started.isoformat(),
            'time_finished': self.time_finished.isoformat(),
            'time_elapsed': self.time_elapsed.total_seconds(),
            'errors': json.dumps(self.errors, indent=2),
            'warnings': json.dumps(self.warnings, indent=2),
            'state': self.state_value,
        }

    @classmethod
    def fields_discovery(cls, host, name, state_topic, root) -> dict[str, Any]:
        device_id = f'duplicacy_{host}_{name}'
        return {
            f'{root}/{"binary_sensor" if field.type is bool else "sensor"}/{device_id}/{field.name}/config': {
                'device': {
                    'identifiers': [device_id],
                    'name': f'{host}/{name} Backup'
                },
                'entity_category': 'diagnostic',
                'object_id': f'{device_id}_{field.name}',
                'state_topic': state_topic,
                'unique_id': f'{device_id}_{field.name}',
                'value_template': f'{{{{ value_json.{field.name} }}}}',
                **({'json_attributes_topic': state_topic} if 'json_attributes_template' in field.metadata else {}),
                **field.metadata
            }
            for field in fields(cls)
        }
