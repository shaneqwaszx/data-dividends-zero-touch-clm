"""Native-first page extraction plus bounded local OCR for the provisional POC."""

import re
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from app.connectors.document_ownership_parser import parse_ownership_observations
from app.connectors.idp import (
    IdpDocumentInput,
    IdpProviderMetadata,
    IdpSourceField,
    IdpSourceResult,
    LocalDocumentProcessingError,
)
from app.connectors.local_document_runtime import isolated_document_pages
from app.connectors.local_ocr import LocalOcrAdapter, TesseractOcrAdapter
from app.domain.documents import (
    ClassificationObservationValues,
    DocumentFieldCandidate,
    DocumentFieldKey,
    DocumentPageEvidence,
    ExtractionMethod,
    ExtractionQuality,
    ExtractionScoreKind,
    GovernmentStatusObservationValues,
    IdpEnvironment,
    OwnershipObservationValues,
)
from app.domain.target_classification import TargetClassificationKey

_FIELD_LABELS: dict[DocumentFieldKey, tuple[str, ...]] = {
    DocumentFieldKey.LEGAL_NAME: ("Legal Name", "Company", "Company / Legal Name"),
    DocumentFieldKey.REGISTRATION_NUMBER: ("UEN", "Registration Number"),
    DocumentFieldKey.REGISTERED_ADDRESS: ("Registered Address",),
    DocumentFieldKey.COUNTRY_OF_INCORPORATION: ("Country", "Country of Incorporation"),
}
# D-101 exact agreement / Government-status labels. A percentage is an exact decimal; the
# partner type is taken only when the line states it (never inferred from the name).
_PARTNER_SHARE = re.compile(
    r"(?im)^[ \t]*Partner Share[ \t]*:[ \t]*([^:\r\n]+?)[ \t]*:[ \t]*"
    r"(\d{1,3}(?:\.\d{1,6})?)[ \t]*percent"
    r"(?:[ \t]*:[ \t]*(NATURAL_PERSON|LEGAL_ENTITY))?[ \t]*$"
)
_AGREEMENT_DATE = re.compile(r"(?im)^[ \t]*Agreement Date[ \t]*:[ \t]*(\d{4}-\d{2}-\d{2})[ \t]*$")
# A line that is itself a "Label:" (a few words, then a colon), so never another label's value.
_LABEL_LINE = re.compile(r"^[A-Za-z][A-Za-z0-9 /&()'.-]{0,60}:")
# A numbered heading ("4. Fields ...", "2) ...") or a bulleted line: never a next-line value.
_LIST_LINE = re.compile(r"^(?:\d{1,3}[.)]\s|[-*•–]\s)")
_FOUNDING_INSTRUMENT = re.compile(r"(?im)^[ \t]*Founding Instrument[ \t]*:[ \t]*([^\r\n]+)[ \t]*$")
_MAX_TEXT = 64_000
_TOTAL_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class _Page:
    text: str = field(repr=False)
    evidence: DocumentPageEvidence


class LocalPdfTextIdpProvider:
    """Extend the existing local port without external transfer or inference.

    Native label scores are 0.97 (primary) / 0.90 (alternate); OCR label scores multiply
    that score by the page's arithmetic mean valid word confidence / 100. Ambiguity
    is capped at 0.40; absence is 0.00. Scores are deterministic evidence, not
    probabilities. Registry comparison never changes extraction evidence.
    """

    def __init__(self, *, ocr: LocalOcrAdapter | None = None) -> None:
        self._ocr = ocr or TesseractOcrAdapter()

    @property
    def metadata(self) -> object:
        return IdpProviderMetadata(provider_name="LOCAL_PDF_TEXT", environment=IdpEnvironment.LOCAL)

    def process(self, document: IdpDocumentInput) -> IdpSourceResult:
        # Native PDFium, Office, TXT and OCR have different line separators.
        # Normalize separators once at the parser boundary, preserving values and
        # page identities. A CRLF is one line, as is a standalone CR.
        pages = tuple(
            _Page(page.text.replace("\r\n", "\n").replace("\r", "\n"), page.evidence)
            for page in self._extract_pages(document)
        )
        ownership = tuple(
            observation
            for page in pages
            for observation in parse_ownership_observations(
                page.text,
                page=page.evidence,
                evidence_score=self._score(page.evidence, primary=True),
            )
        )
        fields = [self._field_from_pages(pages, key) for key in DocumentFieldKey]
        uen = next(
            item.value for item in fields if item.field_key == DocumentFieldKey.REGISTRATION_NUMBER
        )
        ownership = (*ownership, *self._partner_shares_from_pages(pages, uen))
        if len(ownership) > 128:
            raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
        return IdpSourceResult(
            profile=document.profile,
            fields=fields,
            pages=tuple(page.evidence for page in pages),
            ownership_observations=ownership,
            classification_observations=self._classification_from_pages(pages),
            government_status_observations=self._government_status_from_pages(pages),
        )

    def _partner_shares_from_pages(
        self, pages: tuple[_Page, ...], uen: str | None
    ) -> tuple[OwnershipObservationValues, ...]:
        """D-101: exact `Partner Share: <name>: <n> percent[: <type>]` agreement lines.

        Each row is a proposal for the document's single labelled UEN; the RM confirms it.
        Without a unique UEN, or with more than one agreement date, no row is proposed.
        """
        rows: list[tuple[_Page, int, str, Decimal, str | None]] = []
        dates: set[str] = set()
        for page in pages:
            for match in _PARTNER_SHARE.finditer(page.text):
                row = page.text[: match.start()].count("\n") + 1
                rows.append(
                    (page, row, match.group(1).strip(), Decimal(match.group(2)), match.group(3))
                )
            dates.update(match.group(1) for match in _AGREEMENT_DATE.finditer(page.text))
        if len(rows) > 64:
            raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
        if not rows or uen is None or len(dates) > 1:
            return ()
        try:
            as_of = date.fromisoformat(next(iter(dates))) if dates else None
        except ValueError:
            return ()
        observations: list[OwnershipObservationValues] = []
        for page, row, name, percent, owner_type in rows:
            try:
                observations.append(
                    OwnershipObservationValues(
                        **page.evidence.model_dump(exclude={"page_number", "source_reference"}),
                        page_number=page.evidence.page_number,
                        source_reference=f"PAGE_{page.evidence.page_number}_PARTNER_SHARE_ROW_{row}",
                        evidence_score=self._score(page.evidence, primary=True),
                        owner_name=name,
                        owner_type=owner_type,
                        owned_entity_registration_identifier=uen,
                        explicit_percentage=percent,
                        as_of_date=as_of,
                    )
                )
            except ValidationError:
                return ()
        return tuple(observations)

    def _government_status_from_pages(
        self, pages: tuple[_Page, ...]
    ) -> tuple[GovernmentStatusObservationValues, ...]:
        """D-101: exact `Founding Instrument:` lines; never a Government status decision."""
        observations: list[GovernmentStatusObservationValues] = []
        for page in pages:
            for match in _FOUNDING_INSTRUMENT.finditer(page.text):
                value = match.group(1).strip()
                if not value:
                    continue
                if len(value) > 160:
                    raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
                row = page.text[: match.start()].count("\n") + 1
                observations.append(
                    GovernmentStatusObservationValues(
                        **page.evidence.model_dump(exclude={"source_reference"}),
                        field_key="FOUNDING_INSTRUMENT",
                        value=value,
                        evidence_score=self._score(page.evidence, primary=True),
                        source_reference=f"PAGE_{page.evidence.page_number}_LINE_{row}",
                    )
                )
        if len(observations) > 8:
            raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
        return tuple(observations)

    def _classification_from_pages(
        self, pages: tuple[_Page, ...]
    ) -> tuple[ClassificationObservationValues, ...]:
        observations: list[ClassificationObservationValues] = []
        labels = {
            TargetClassificationKey.KYC_CUSTOMER_TYPE: "KYC Customer Type",
            TargetClassificationKey.CLIENT_SEGMENT: "Client Segment",
        }
        for page in pages:
            lines = page.text.split("\n")
            for key, label in labels.items():
                # The label, optionally with a short qualifier ("KYC Customer Type (suggested):"),
                # then its value on the same line or, when nothing follows the colon, on the
                # very next line (a common layout). A blank next line or another "Label:" line
                # is never taken as a value; nothing is read without its label.
                pattern = re.compile(
                    rf"(?i)^[ \t]*{re.escape(label)}"
                    rf"(?:[ \t]*\([^()\n]{{1,40}}\))?[ \t]*:[ \t]*(.*)$"
                )
                for index, line in enumerate(lines):
                    match = pattern.match(line)
                    if match is None:
                        continue
                    value = match.group(1).strip()
                    row = index + 1
                    if not value and index + 1 < len(lines):
                        candidate = lines[index + 1].strip()
                        # Not another label, a numbered heading or a bullet, and never a long
                        # line (prose is skipped, not an error: the rest of the document reads).
                        if (
                            candidate
                            and len(candidate) <= 160
                            and not _LABEL_LINE.match(candidate)
                            and not _LIST_LINE.match(candidate)
                        ):
                            value, row = candidate, index + 2
                    if not value:
                        continue
                    if len(value) > 160:
                        raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
                    observations.append(
                        ClassificationObservationValues(
                            **page.evidence.model_dump(exclude={"source_reference"}),
                            field_key=key,
                            value=value,
                            evidence_score=self._score(page.evidence, primary=True),
                            source_reference=f"PAGE_{page.evidence.page_number}_LINE_{row}",
                        )
                    )
        if len(observations) > 64:
            raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
        return tuple(observations)

    def _extract_pages(self, document: IdpDocumentInput) -> tuple[_Page, ...]:
        if document.extracted_text is not None:
            if len(document.extracted_text) > _MAX_TEXT:
                raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
            method = (
                ExtractionMethod.NATIVE_DOCX_TEXT
                if document.media_type.startswith("application/vnd.openxmlformats")
                else ExtractionMethod.NATIVE_TXT_TEXT
            )
            # DOCX/TXT have no reliable rendered page number: logical extraction unit 1.
            return (_Page(document.extracted_text, self._evidence(1, method)),)
        started = time.monotonic()
        pages: list[_Page] = []
        total_text = 0
        with isolated_document_pages(document.content, document.media_type) as source_pages:
            for page in source_pages:
                remaining = _TOTAL_TIMEOUT_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    raise LocalDocumentProcessingError("DOCUMENT_PROCESSING_TIMEOUT")
                if page.image_path is None:
                    text = page.text
                    evidence = self._evidence(page.page_number, ExtractionMethod.NATIVE_PDF_TEXT)
                else:
                    result = self._ocr.recognize(page.image_path, timeout_seconds=remaining)
                    text = result.text
                    evidence = self._evidence(
                        page.page_number,
                        ExtractionMethod.LOCAL_TESSERACT_OCR,
                        raw_mean=result.raw_mean_confidence,
                        word_count=result.word_count,
                    )
                total_text += len(text)
                if total_text > _MAX_TEXT:
                    raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
                if not text.strip():
                    evidence = evidence.model_copy(
                        update={
                            "extraction_quality": ExtractionQuality.UNAVAILABLE,
                        }
                    )
                pages.append(_Page(text, evidence))
        if time.monotonic() - started > _TOTAL_TIMEOUT_SECONDS:
            raise LocalDocumentProcessingError("DOCUMENT_PROCESSING_TIMEOUT")
        return tuple(pages)

    @staticmethod
    def _evidence(
        page_number: int,
        method: ExtractionMethod,
        *,
        raw_mean: float | None = None,
        word_count: int | None = None,
    ) -> DocumentPageEvidence:
        ocr = method == ExtractionMethod.LOCAL_TESSERACT_OCR
        quality = ExtractionQuality.HIGH
        if ocr:
            quality = (
                ExtractionQuality.UNAVAILABLE
                if raw_mean is None
                else ExtractionQuality.HIGH
                if raw_mean >= 85
                else ExtractionQuality.LOW
            )
        return DocumentPageEvidence(
            page_number=page_number,
            source_reference=f"PAGE_{page_number}",
            extraction_method=method,
            extraction_quality=quality,
            score_kind=ExtractionScoreKind.DETERMINISTIC_EVIDENCE_SCORE,
            score_formula="LABEL_SCORE_TIMES_OCR_MEAN_OVER_100" if ocr else "LABEL_SCORE",
            raw_ocr_mean_confidence=raw_mean,
            raw_ocr_word_count=word_count,
        )

    @staticmethod
    def _score(evidence: DocumentPageEvidence, *, primary: bool) -> float:
        score = 0.97 if primary else 0.90
        if evidence.extraction_method == ExtractionMethod.LOCAL_TESSERACT_OCR:
            score *= (evidence.raw_ocr_mean_confidence or 0.0) / 100
        return round(score, 6)

    def _field_from_pages(self, pages: tuple[_Page, ...], key: DocumentFieldKey) -> IdpSourceField:
        candidates: list[tuple[DocumentFieldCandidate, bool]] = []
        for page in pages:
            for index, label in enumerate(_FIELD_LABELS[key]):
                pattern = re.compile(rf"(?im)^\s*{re.escape(label)}\s*:\s*([^\r\n]+)\s*$")
                for match in pattern.finditer(page.text):
                    value = match.group(1).strip()
                    if len(value) > 512:
                        raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
                    if value:
                        row = page.text[: match.start()].count("\n") + 1
                        candidates.append(
                            (
                                DocumentFieldCandidate(
                                    **page.evidence.model_dump(exclude={"source_reference"}),
                                    value=value,
                                    source_reference=f"PAGE_{page.evidence.page_number}_LINE_{row}",
                                ),
                                index == 0,
                            )
                        )
        if len(candidates) > 32:
            raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
        distinct = set(candidate.value for candidate, _ in candidates)
        if not candidates:
            no_text = not any(page.text.strip() for page in pages)
            return IdpSourceField(
                field_key=key,
                value=None,
                confidence=0.0,
                source_reference="DOCUMENT_TEXT_UNAVAILABLE" if no_text else "LABEL_MISSING",
                extraction_quality=ExtractionQuality.UNAVAILABLE,
                score_kind=ExtractionScoreKind.DETERMINISTIC_EVIDENCE_SCORE,
                score_formula="LABEL_SCORE",
                candidates=(),
            )
        first, primary = max(
            candidates,
            key=lambda item: self._score(
                DocumentPageEvidence.model_validate(item[0].model_dump(exclude={"value"})),
                primary=item[1],
            ),
        )
        evidence = DocumentPageEvidence.model_validate(first.model_dump(exclude={"value"}))
        ambiguous = len(distinct) > 1
        return IdpSourceField(
            **evidence.model_dump(exclude={"source_reference", "extraction_quality"}),
            extraction_quality=(
                ExtractionQuality.AMBIGUOUS if ambiguous else first.extraction_quality
            ),
            field_key=key,
            value=None if ambiguous else first.value,
            confidence=min(0.4, self._score(evidence, primary=primary))
            if ambiguous
            else self._score(evidence, primary=primary),
            source_reference="AMBIGUOUS_LABELLED_VALUES" if ambiguous else "UNIQUE_LABELLED_TEXT",
            candidates=tuple(candidate for candidate, _ in candidates),
        )
