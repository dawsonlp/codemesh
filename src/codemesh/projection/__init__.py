"""FileSystem Projection & Materialization package."""

from codemesh.projection.file_projector import FileSystemProjector, MaterializedFile
from codemesh.projection.import_synthesizer import ImportSynthesizer

__all__ = [
    "ImportSynthesizer",
    "FileSystemProjector",
    "MaterializedFile",
]

