from dataclasses import dataclass
import json
import logging
import platform
from typing import Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

@dataclass
class Config:
    mqtt_hostname: str
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None

class UpdateHandler:
    def __init__(self, configfile, backup_name):
        with open(configfile, 'r') as f:
            self.config = Config(**json.load(f))

        def on_connect(client, userdata, flags, reason_code, properties):
            logger.info('Connected with result code %s', reason_code)

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = on_connect
        if self.config.mqtt_username:
            self.client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)
        self.client.connect(self.config.mqtt_hostname, self.config.mqtt_port)

        self.topic = f'duplicacy/{platform.node()}/{backup_name}'
        self.client.loop_start()

    def send_completion(self, state):
        self.client.publish(self.topic, json.dumps(state.as_dict()), 1, True)
        self.client.loop_stop()

    def send_progress(self, state):
        self.client.publish(f'{self.topic}/progress', json.dumps(state.as_dict()), 1, True)
