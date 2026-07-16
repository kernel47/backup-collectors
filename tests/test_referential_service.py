from models import Settings
from services.referential import get_asset


def test_referential_resolves_hostname_to_asset(monkeypatch):
    request = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hostname": "master-01",
                "api_username": "api-user",
                "api_password": "api-secret",
                "domain_type": "unixpwd",
                "domain_name": "master-01",
                "version": "11.0",
                "ssh_username": "ssh-user",
                "ssh_password": "ssh-secret",
                "api": True,
                "ssh": "true",
                "region": "emea",
                "datacenter": "paris-01",
            }

    def fake_get(url, **kwargs):
        request["url"] = url
        request["headers"] = kwargs["headers"]
        return Response()

    monkeypatch.setattr("services.referential.httpx.get", fake_get)
    settings = Settings(
        referential_asset_url="https://referential.example.test/assets/{hostname}",
        referential_token="token",
    )
    asset = get_asset("master-01", settings)

    assert request["url"] == "https://referential.example.test/assets/master-01"
    assert request["headers"]["Authorization"] == "Bearer token"
    assert asset.hostname == "master-01"
    assert asset.api_username == "api-user"
    assert asset.ssh_username == "ssh-user"
    assert asset.api is True
    assert asset.ssh is True
    assert asset.region == "emea"
    assert asset.datacenter == "paris-01"
    assert "api-secret" not in repr(asset)
    assert "ssh-secret" not in repr(asset)
