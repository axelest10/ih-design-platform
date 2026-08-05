import json
from pathlib import Path

from jsonschema import Draft202012Validator
from rest_framework import serializers

from .models import DesignBrief


def validate_brief_contract(data):
    schema_path = Path(__file__).resolve().parents[2] / "contracts" / "design-brief.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda error: error.path)
    if errors:
        raise serializers.ValidationError({"contract": [error.message for error in errors]})


class DesignBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignBrief
        fields = "__all__"

    def validate(self, attrs):
        instance = self.instance
        payload = {
            "title": attrs.get("title", instance.title if instance else None),
            "format": attrs.get("format", instance.format if instance else None),
            "audience": attrs.get("audience", instance.audience if instance else None),
            "objective": attrs.get("objective", instance.objective if instance else None),
            "requested_message": attrs.get(
                "requested_message", instance.requested_message if instance else ""
            ),
            "source_references": attrs.get(
                "source_references", instance.source_references if instance else []
            ),
            "constraints": attrs.get("constraints", instance.constraints if instance else {}),
        }
        validate_brief_contract(payload)
        return attrs
