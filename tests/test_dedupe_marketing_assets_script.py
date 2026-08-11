from scripts.dedupe_marketing_assets import find_duplicate_groups, run_dedupe


class StubResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class StubSession:
    cookies = {"csrftoken": "csrf-token"}

    def __init__(self, assets):
        self.assets = assets
        self.deleted = []

    def get(self, url, **kwargs):
        assert url == "https://example.test/api/v1/marketing-assets/"
        return StubResponse(self.assets)

    def delete(self, url, **kwargs):
        self.deleted.append(url)
        return StubResponse({})


class StubRequests:
    RequestException = OSError


def _assets():
    duplicate = {
        "brand": "ih",
        "country": "MX",
        "category": "foto_perfil",
        "label": "Perfil IH",
    }
    return [
        {"id": 9, **duplicate},
        {"id": 3, **duplicate},
        {"id": 7, **duplicate},
        {
            "id": 4,
            "brand": "ielts",
            "country": "",
            "category": "firma_electronica",
            "label": "Firma IELTS",
        },
    ]


def test_duplicate_group_keeps_lowest_id():
    groups = find_duplicate_groups(_assets())

    assert len(groups) == 1
    assert groups[0].keep["id"] == 3
    assert [asset["id"] for asset in groups[0].delete] == [7, 9]


def test_dedupe_dry_run_never_deletes(capsys):
    session = StubSession(_assets())

    result = run_dedupe(
        session,
        "https://example.test",
        StubRequests,
        execute=False,
    )

    assert result == 0
    assert session.deleted == []
    output = capsys.readouterr().out
    assert "Conservar ID" in output
    assert "elementos_por_borrar=2" in output
    assert "Dry-run: no se borró ningún material." in output
