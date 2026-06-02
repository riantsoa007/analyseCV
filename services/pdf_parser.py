class PDFParser:
    @staticmethod
    def extract_text(file_path):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Le package pypdf n'est pas installe.") from exc

        reader = PdfReader(file_path)
        text_parts = []

        for page in reader.pages:
            text_parts.append(page.extract_text() or "")

        return "\n".join(text_parts)
