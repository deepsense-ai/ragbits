from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from docling_core.types.doc import DoclingDocument
from pptx.presentation import Presentation


class PptxCallback(ABC):
    """
    Abstract base class for PPTX document enhancement callbacks.
    """

    name: str

    @abstractmethod
    def __call__(
        self, pptx_path: Path, presentation: Presentation, docling_document: DoclingDocument
    ) -> DoclingDocument:
        """
        Process PPTX presentation and enhance the docling document.

        Args:
            pptx_path: Path to the PPTX file.
            presentation: Loaded PPTX presentation.
            docling_document: Document to enhance.

        Returns:
            Enhanced docling document.
        """
        pass
