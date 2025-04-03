import re
import base64
from bs4 import BeautifulSoup


def bs64_to_utf8(encoded_data: str) -> str:
    bytes_ = encoded_data.encode(encoding="ASCII")
    decoded_bytes = base64.urlsafe_b64decode(bytes_)
    data = decoded_bytes.decode("utf-8")
    return data


def process_html(html: str) -> str:
    soup = BeautifulSoup(html, features="html.parser")
    text = soup.get_text()
    text = text.replace("\n"," ")
    text = re.sub(pattern=r"\s+", repl=" ", string=text).strip()
    return text
