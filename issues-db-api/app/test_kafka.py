from app import kafka


def test_send_ui_update():
    kafka.send_ui_update()
    # print(kafka.receive_ui_update())
