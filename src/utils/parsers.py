import base64


def bs64_to_utf8(encoded_data: str) -> str:
    bytes_ = encoded_data.encode(encoding="ASCII")
    decoded_bytes = base64.urlsafe_b64decode(bytes_)
    data = decoded_bytes.decode("utf-8")
    return data