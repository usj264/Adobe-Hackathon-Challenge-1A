#!/usr/bin/env python3

import json
import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

try:
    import PyPDF2
    import pdfplumber
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFOutlineExtractor:
    def __init__(self):
        self.heading_patterns = [
            r'^(\d+\.)\s+(.+)$',
            r'^(\d+\.\d+)\s+(.+)$',
            r'^(\d+\.\d+\.\d+)\s+(.+)$',
            r'^(Chapter\s+\d+)[:\.\s]*(.*)$',
            r'^(CHAPTER\s+\d+)[:\.\s]*(.*)$',
            r'^(Section\s+\d+)[:\.\s]*(.*)$',
            r'^(SECTION\s+\d+)[:\.\s]*(.*)$',
            r'^(Appendix\s+[A-Z])[:\.\s]*(.*)$',
            r'^(APPENDIX\s+[A-Z])[:\.\s]*(.*)$',
            r'^([IVX]+\.)\s+(.+)$',
            r'^([A-Z]\.)\s+(.+)$',
        ]
        self.font_thresholds = {'H1': 16.0, 'H2': 14.0, 'H3': 12.0}

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'\s+\d+\s*$', '', text)
        text = text.rstrip('.')
        return text

    def extract_title_from_metadata(self, pdf_path: str) -> Optional[str]:
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if reader.metadata:
                    title = reader.metadata.get('/Title', '').strip()
                    if title and len(title) > 3:
                        return self.clean_text(title)
        except Exception as e:
            logger.debug(f"Metadata title extraction failed: {e}")
        return None

    def extract_title_from_content(self, pdf_path: str) -> str:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    return Path(pdf_path).stem.replace('_', ' ').replace('-', ' ').title()
                text = pdf.pages[0].extract_text()
                if not text:
                    return Path(pdf_path).stem.replace('_', ' ').replace('-', ' ').title()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for i, line in enumerate(lines[:10]):
                    line = self.clean_text(line)
                    if len(line) < 3 or re.match(r'^[\d\W]+$', line):
                        continue
                    if any(w in line.lower() for w in ['page', 'copyright', 'www.', 'http']):
                        continue
                    if 10 <= len(line) <= 100 and not line.endswith(':'):
                        return line
                for line in lines:
                    line = self.clean_text(line)
                    if len(line) >= 10:
                        return line
        except Exception as e:
            logger.error(f"Title extraction failed: {e}")
        return Path(pdf_path).stem.replace('_', ' ').replace('-', ' ').title()

    def extract_title(self, pdf_path: str) -> str:
        return self.extract_title_from_metadata(pdf_path) or self.extract_title_from_content(pdf_path)

    def classify_heading_level(self, text: str, line_position: int = 0, font_size: Optional[float] = None) -> str:
        text = text.strip()
        for pattern in self.heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                if re.match(r'^\d+\.$', text):
                    return "H1"
                elif re.match(r'^\d+\.\d+$', text):
                    return "H2"
                elif re.match(r'^\d+\.\d+\.\d+$', text):
                    return "H3"
                elif 'chapter' in text.lower() or 'appendix' in text.lower():
                    return "H1"
        if font_size:
            if font_size >= self.font_thresholds['H1']:
                return "H1"
            elif font_size >= self.font_thresholds['H2']:
                return "H2"
            elif font_size >= self.font_thresholds['H3']:
                return "H3"
        return "H2" if text.istitle() else "H3"

    def is_likely_heading(self, text: str) -> bool:
        if len(text) < 3 or len(text) > 150:
            return False
        if text.endswith(('.', ',', ';', '!', '?')):
            return False
        if text.isupper() and len(text) < 60:
            return True
        if re.match(r'^[\d\w]+[\.\)]\s+', text):
            return True
        if text.istitle() and 5 <= len(text) <= 60:
            return True
        return False

    def extract_outline(self, pdf_path: str) -> Dict[str, Any]:
        outline = {"title": self.extract_title(pdf_path), "outline": []}
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 0):
                    text = page.extract_text()
                    if not text:
                        continue
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        line = self.clean_text(line)
                        if not line or not self.is_likely_heading(line):
                            continue
                        level = self.classify_heading_level(line, i)
                        if not any(h["text"] == line and h["page"] == page_num for h in outline["outline"]):
                            outline["outline"].append({"level": level, "text": line, "page": page_num})
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
        return outline

def process_pdfs():
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    extractor = PDFOutlineExtractor()
    output_dir.mkdir(parents=True, exist_ok=True)
    for pdf_path in input_dir.glob("*.pdf"):
        try:
            result = extractor.extract_outline(str(pdf_path))
            with open(output_dir / f"{pdf_path.stem}.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            logger.error(f"Failed on {pdf_path.name}: {e}")
            with open(output_dir / f"{pdf_path.stem}.json", "w", encoding="utf-8") as f:
                json.dump({"title": pdf_path.stem, "outline": []}, f, indent=2)

if __name__ == "__main__":
    os.environ['PYTHONUNBUFFERED'] = '1'
    process_pdfs()
