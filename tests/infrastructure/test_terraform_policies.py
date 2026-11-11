"""Reglas de seguridad para la infraestructura de AWS.

Son revisiones sencillas sobre el código de Terraform para mostrar la idea de
"política como código": si alguien abre SSH o quita el cifrado, el PR falla.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN_TF = (ROOT / "infra" / "terraform" / "aws-ec2" / "main.tf").read_text(encoding="utf-8")


def resource_block(resource_type: str, name: str) -> str:
    start = MAIN_TF.index(f'resource "{resource_type}" "{name}"')
    depth = 0
    for index in range(MAIN_TF.index("{", start), len(MAIN_TF)):
        if MAIN_TF[index] == "{":
            depth += 1
        elif MAIN_TF[index] == "}":
            depth -= 1
            if depth == 0:
                return MAIN_TF[start : index + 1]
    raise AssertionError(f"Bloque incompleto: {resource_type}.{name}")


def test_ssh_port_is_not_open():
    security_group = resource_block("aws_security_group", "web")
    ports = {int(port) for port in re.findall(r"(?:from|to)_port\s*=\s*(\d+)", security_group)}

    assert 22 not in ports


def test_instance_requires_imdsv2():
    instance = resource_block("aws_instance", "application")

    assert re.search(r'http_tokens\s*=\s*"required"', instance)


def test_root_volume_is_encrypted():
    instance = resource_block("aws_instance", "application")

    assert re.search(r"encrypted\s*=\s*true", instance)


def test_artifact_bucket_blocks_public_access():
    block = resource_block("aws_s3_bucket_public_access_block", "artifacts")

    for setting in (
        "block_public_acls",
        "block_public_policy",
        "ignore_public_acls",
        "restrict_public_buckets",
    ):
        assert re.search(rf"{setting}\s*=\s*true", block), setting


def test_artifact_bucket_is_encrypted():
    assert 'resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts"' in MAIN_TF
