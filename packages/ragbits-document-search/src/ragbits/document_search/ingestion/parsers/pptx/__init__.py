from .callbacks import PptxCallback
from .exceptions import (
    PptxExtractionError,
    PptxParserError,
    PptxPresentationError,
)
from .hyperlink_callback import LinkCallback
from .metadata_callback import MetaCallback
from .parser import PptxDocumentParser
from .speaker_notes_callback import NotesCallback

DEFAULT_CALLBACKS = [
    NotesCallback(),
    LinkCallback(),
    MetaCallback(),
]

__all__ = [
    "DEFAULT_CALLBACKS",
    "LinkCallback",
    "MetaCallback",
    "NotesCallback",
    "PptxCallback",
    "PptxDocumentParser",
    "PptxExtractionError",
    "PptxParserError",
    "PptxPresentationError",
]
