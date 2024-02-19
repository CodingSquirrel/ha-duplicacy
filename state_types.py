from dataclasses import dataclass, field, fields, asdict
from datetime import datetime, timedelta
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
    revision: int = 0
    time_started: datetime = datetime.fromtimestamp(0)
    time_finished: datetime = datetime.fromtimestamp(0)
    time_elapsed: timedelta = timedelta()
    files: int = 0
    files_size: int = 0
    new_files: int = 0
    new_files_size: int = 0
    chunks: int = 0
    chunks_size: int = 0
    new_chunks: int = 0
    new_chunks_size: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def state(self) -> str:
        if self.errors:
            return 'error'
        if self.warnings:
            return 'warning'
        return 'success'

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            'time_started': str(self.time_started),
            'time_finished': str(self.time_finished),
            'time_elapsed': str(self.time_elapsed),
            'state': self.state
        }

    @classmethod
    def fields_discovery(cls, host, name, state_topic) -> dict[str, Any]:
        device_id = f'duplicacy_{host}_{name}'
        return [
            {
                'device': {
                    'identifiers': [device_id],
                    'name': f'{host}/{name} Backup'
                },
                'entity_category': 'diagnostic',
                'object_id': f'{device_id}_{field.name}',
                'state_topic': state_topic,
                'unique_id': f'{device_id}_{field.name}',
                'value_template': f'{{{{ value_json.{field.name}}}}}',
                **field.metadata
            }
            for field in fields(cls)
        ]
