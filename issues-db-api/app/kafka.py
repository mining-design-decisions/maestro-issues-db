from kafka import KafkaConsumer, KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)
consumer = KafkaConsumer(
    "ui_updates_topic",
    bootstrap_servers=["localhost:9092"],
    group_id=None,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)


def send_ui_update():
    producer.send("ui_updates_topic", {"data": "values"})


def receive_ui_update():
    print(next(consumer))
