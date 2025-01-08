from dataclasses import dataclass

@dataclass(frozen=True)
class FileDescription:
    contents: str
    image_file_path: str