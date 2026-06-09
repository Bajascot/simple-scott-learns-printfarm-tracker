from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.integrations.govee import get_device_energy, get_devices

# ---------------------------------------------------------------------------
# Fake Govee API responses
# ---------------------------------------------------------------------------

FAKE_DEVICES = [
    {"device": "AA:BB:CC:DD:EE:FF:00:11", "model": "H5083", "deviceName": "Printer 1 Plug"},
    {"device": "11:22:33:44:55:66:77:88", "model": "H5083", "deviceName": "Printer 2 Plug"},
]

FAKE_STATE_RESPONSE = {
    "data": {
        "device": "AA:BB:CC:DD:EE:FF:00:11",
        "model": "H5083",
        "properties": [
            {"online": True},
            {"powerState": "on"},
            {"powerConsumption": 85.4},
        ],
    }
}


def mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# get_devices
# ---------------------------------------------------------------------------

class TestGetDevices:
    def test_returns_device_list(self):
        with patch('httpx.Client') as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = mock_response({"data": {"devices": FAKE_DEVICES}})

            result = get_devices("test-api-key")

        assert len(result) == 2
        assert result[0]["device"] == "AA:BB:CC:DD:EE:FF:00:11"
        assert result[0]["model"] == "H5083"

    def test_passes_api_key_header(self):
        with patch('httpx.Client') as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = mock_response({"data": {"devices": FAKE_DEVICES}})

            get_devices("my-secret-key")

            _, kwargs = mock_client.get.call_args
            assert kwargs['headers']['Govee-API-Key'] == 'my-secret-key'

    def test_returns_empty_list_on_network_error(self):
        with patch('httpx.Client') as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.side_effect = httpx.ConnectError("unreachable")

            result = get_devices("test-api-key")

        assert result == []

    def test_returns_empty_list_on_http_error(self):
        with patch('httpx.Client') as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            resp = mock_response({}, status_code=401)
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401", request=MagicMock(), response=resp
            )
            mock_client.get.return_value = resp

            result = get_devices("bad-key")

        assert result == []

    def test_returns_empty_list_when_no_devices_key(self):
        with patch('httpx.Client') as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = mock_response({"data": {}})

            result = get_devices("test-api-key")

        assert result == []


# ---------------------------------------------------------------------------
# get_device_energy
# ---------------------------------------------------------------------------

class TestGetDeviceEnergy:
    def test_returns_power_consumption(self):
        with patch('httpx.Client') as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = mock_response(FAKE_STATE_RESPONSE)

            watts = get_device_energy("AA:BB:CC:DD:EE:FF:00:11", "H5083", "test-api-key")

        assert watts == pytest.approx(85.4)

    def test_returns_none_when_property_missing(self):
        state_no_power = {
            "data": {
                "properties": [{"online": True}, {"powerState": "on"}]
            }
        }
        with patch('httpx.Client') as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = mock_response(state_no_power)

            watts = get_device_energy("AA:BB", "H5083", "test-api-key")

        assert watts is None

    def test_returns_none_on_network_error(self):
        with patch('httpx.Client') as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.side_effect = httpx.ConnectError("unreachable")

            watts = get_device_energy("AA:BB", "H5083", "test-api-key")

        assert watts is None

    def test_passes_device_and_model_as_params(self):
        with patch('httpx.Client') as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = mock_response(FAKE_STATE_RESPONSE)

            get_device_energy("AA:BB:CC", "H5083", "test-api-key")

            _, kwargs = mock_client.get.call_args
            assert kwargs['params']['device'] == 'AA:BB:CC'
            assert kwargs['params']['model'] == 'H5083'


# ---------------------------------------------------------------------------
# GET /api/govee/status
# ---------------------------------------------------------------------------

class TestGoveeStatus:
    def test_not_configured(self, client):
        with patch('backend.routers.govee.settings') as mock_settings:
            mock_settings.GOVEE_API_KEY = None
            r = client.get('/api/govee/status')
        assert r.status_code == 200
        assert r.json() == {'configured': False}

    def test_configured(self, client):
        with patch('backend.routers.govee.settings') as mock_settings:
            mock_settings.GOVEE_API_KEY = 'some-key'
            r = client.get('/api/govee/status')
        assert r.status_code == 200
        assert r.json() == {'configured': True}


# ---------------------------------------------------------------------------
# GET /api/govee/devices
# ---------------------------------------------------------------------------

class TestGoveeDevices:
    def test_returns_400_when_key_not_configured(self, client):
        with patch('backend.routers.govee.settings') as mock_settings:
            mock_settings.GOVEE_API_KEY = None
            r = client.get('/api/govee/devices')
        assert r.status_code == 400

    def test_returns_device_list(self, client):
        with patch('backend.routers.govee.settings') as mock_settings, \
             patch('backend.routers.govee.get_devices', return_value=FAKE_DEVICES):
            mock_settings.GOVEE_API_KEY = 'real-key'
            r = client.get('/api/govee/devices')
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_returns_empty_list_when_govee_unreachable(self, client):
        with patch('backend.routers.govee.settings') as mock_settings, \
             patch('backend.routers.govee.get_devices', return_value=[]):
            mock_settings.GOVEE_API_KEY = 'real-key'
            r = client.get('/api/govee/devices')
        assert r.status_code == 200
        assert r.json() == []


# ---------------------------------------------------------------------------
# GET /api/govee/devices/{device_id}/power
# ---------------------------------------------------------------------------

class TestDevicePower:
    def test_returns_watts(self, client):
        with patch('backend.routers.govee.settings') as mock_settings, \
             patch('backend.routers.govee.get_device_energy', return_value=85.4):
            mock_settings.GOVEE_API_KEY = 'real-key'
            r = client.get('/api/govee/devices/AA:BB/power?model=H5083')
        assert r.status_code == 200
        assert r.json()['watts'] == pytest.approx(85.4)

    def test_returns_503_when_reading_unavailable(self, client):
        with patch('backend.routers.govee.settings') as mock_settings, \
             patch('backend.routers.govee.get_device_energy', return_value=None):
            mock_settings.GOVEE_API_KEY = 'real-key'
            r = client.get('/api/govee/devices/AA:BB/power?model=H5083')
        assert r.status_code == 503

    def test_returns_400_when_key_not_configured(self, client):
        with patch('backend.routers.govee.settings') as mock_settings:
            mock_settings.GOVEE_API_KEY = None
            r = client.get('/api/govee/devices/AA:BB/power?model=H5083')
        assert r.status_code == 400
