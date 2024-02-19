from dataclasses import dataclass
import json
import logging
import platform
from typing import Optional

import paho.mqtt.client as mqtt

from state_types import ProgressState, CompletionState

logger = logging.getLogger(__name__)

class UpdateHandler:
    def __init__(self, mqtt_hostname, mqtt_port, mqtt_username, mqtt_password, discovery_root,  backup_name):
        def on_connect(client, userdata, flags, reason_code, properties):
            logger.info('Connected to MQTT host %s with result code %s', mqtt_hostname, reason_code)

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = on_connect
        if mqtt_username:
            self.client.username_pw_set(mqtt_username, mqtt_password)
        self.client.connect(mqtt_hostname, mqtt_port)
        self.client.loop_start()

        self.backup_host = platform.node()
        self.backup_name = backup_name
        
        self.topic = f'duplicacy/{self.backup_host}/{self.backup_name}'
        self.progress_topic = f'{self.topic}/progress'
        
        progress_fields_discovery = ProgressState.fields_discovery(
            self.backup_host, self.backup_name, self.progress_topic, discovery_root
        )
        for topic, payload in progress_fields_discovery.items():
            self.client.publish(topic, json.dumps(payload), 1, True)

        #completion_fields_discovery = CompletionState.fields_discovery(
        #    self.backup_host, self.backup_name, self.topic, discovery_root
        #)
        #for topic, payload in completion_fields_discovery.items():
        #    self.client.publish(topic, json.dumps(payload), 1, True)

    def send_completion(self, state):
        self.client.publish(self.topic, json.dumps(state.as_dict()), 1, True)
        self.client.loop_stop()

    def send_progress(self, state):
        self.client.publish(self.progress_topic, json.dumps(state.as_dict()), 1, True)
