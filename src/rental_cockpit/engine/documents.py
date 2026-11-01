# Copyright © 2026 Vincent Fournet
"""« Justificatifs » : PDF checks, reading assistance, duplicates and what the screens show.

A PDF is checked for what it is, not for its name (PDF 04): a real PDF
structure, 8 MiB and 200 pages at most, no password needed to open it, no
script, launch action or embedded file. Its content is never run: it is
only parsed to be checked and, for the first pages, to read its text.

Reading the text is an assistance (PDF 03): a date, an amount, an invoice
number and a known supplier may be proposed, each one marked « À vérifier »;
what is not found stays empty, and a scanned PDF without text is entered by
hand. Nothing is ever deduced about a payment.

Duplicates (DUP 01): the same file (same SHA-256, even renamed) or the same
reference (same supplier and same invoice number) is a certain duplicate; the
same supplier, date and amount without a number to tell them apart is a
probable one, which the person confirms. An amount alone is never enough.
"""
from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from datetime import date
from typing import Any

from . import money
from .errors import RCError
from .schema import category_label

MAX_PDF_BYTES = 8 * 1024 * 1024
MAX_PAGES = 200
TEXT_PAGES = 5
TEXT_LIMIT = 200_000
MAX_OBJECTS = 200_000
MAX_DEPTH = 60

# Keys and actions that would make a PDF do something by itself: refused (PDF 04).
FORBIDDEN_KEYS = {"/JavaScript", "/JS", "/Launch", "/EmbeddedFiles", "/EmbeddedFile", "/RichMedia", "/XFA"}
FORBIDDEN_ACTIONS = {"/JavaScript", "/Launch", "/ImportData", "/SubmitForm", "/GoToE", "/RichMediaExecute", "/Rendition"}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalized(value: Any) -> str:
    """Comparison form of a name or a reference: accents, case and spaces do not matter."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return " ".join(text.split())


def reference(value: Any) -> str:
    """Comparison form of an invoice number: « F-018 », « f 018 » and « F018 » are the same."""
    return re.sub(r"[^0-9a-z]", "", normalized(value))


# --------------------------------------------------------------------------- checks

def inspect_pdf(raw: bytes) -> dict[str, Any]:
    """Check a PDF and read the text of its first pages. Raises an explained RCError."""
    from pypdf import PdfReader
    from pypdf.errors import FileNotDecryptedError, LimitReachedError, PdfReadError

    if len(raw) > MAX_PDF_BYTES:
        raise RCError("pdf_too_large")
    if not raw or b"%PDF-" not in raw[:1024] or b"%%EOF" not in raw[-4096:]:
        raise RCError("pdf_invalid")
    try:
        reader = PdfReader(io.BytesIO(raw), strict=False)
        if reader.is_encrypted:
            # Only a PDF that opens without a password is accepted (restrictions alone are fine).
            try:
                if not reader.decrypt(""):
                    raise RCError("pdf_encrypted")
            except (FileNotDecryptedError, NotImplementedError) as exc:
                raise RCError("pdf_encrypted") from exc
        pages = len(reader.pages)
        if pages < 1:
            raise RCError("pdf_invalid")
        if pages > MAX_PAGES:
            raise RCError("pdf_too_complex")
        _refuse_active_content(reader)
        text_parts: list[str] = []
        size = 0
        for page in reader.pages[:TEXT_PAGES]:
            part = page.extract_text() or ""
            text_parts.append(part)
            size += len(part)
            if size > TEXT_LIMIT:
                break
        text = "\n".join(text_parts)[:TEXT_LIMIT]
    except RCError:
        raise
    except (LimitReachedError, RecursionError, MemoryError) as exc:
        raise RCError("pdf_too_complex") from exc
    except (PdfReadError, ValueError, KeyError, TypeError, AttributeError, IndexError, AssertionError, OSError) as exc:
        raise RCError("pdf_invalid") from exc
    except Exception as exc:  # any other parser failure is a file we do not accept, never a crash
        raise RCError("pdf_invalid") from exc
    return {"pages": pages, "size": len(raw), "sha256": sha256(raw), "text": text,
            "text_found": len("".join(text.split())) >= 20}


def _refuse_active_content(reader: Any) -> None:
    """Walk the document's objects: any script, launch action or embedded file refuses it."""
    seen: set[tuple[int, int]] = set()
    budget = [MAX_OBJECTS]

    def walk(obj: Any, depth: int) -> None:
        if depth > MAX_DEPTH:
            raise RCError("pdf_too_complex")
        if hasattr(obj, "idnum") and hasattr(obj, "get_object"):
            key = (obj.idnum, obj.generation)
            if key in seen:
                return
            seen.add(key)
            obj = obj.get_object()
        budget[0] -= 1
        if budget[0] < 0:
            raise RCError("pdf_too_complex")
        if isinstance(obj, dict):
            if FORBIDDEN_KEYS.intersection(str(k) for k in obj):
                raise RCError("pdf_active_content")
            if str(obj.get("/S", "")) in FORBIDDEN_ACTIONS or str(obj.get("/Type", "")) in {"/EmbeddedFile", "/Filespec"} and "/EF" in obj:
                raise RCError("pdf_active_content")
            for key, value in obj.items():
                if str(key) in ("/Parent", "/P"):
                    continue  # back links: already walked from the top
                walk(value, depth + 1)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                walk(value, depth + 1)

    walk(reader.trailer, 0)


# --------------------------------------------------------------------------- reading assistance

_MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "decembre": 12, "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "janv": 1, "fevr": 2, "avr": 4, "juil": 7, "sept": 9, "oct": 10, "nov": 11, "dec": 12, "jan": 1, "feb": 2, "mar": 3,
    "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
}
_DATE = (r"(?P<d1>\d{1,2})[/.\-](?P<m1>\d{1,2})[/.\-](?P<y1>\d{4})"
         r"|(?P<y2>\d{4})-(?P<m2>\d{2})-(?P<d2>\d{2})"
         r"|(?P<d3>\d{1,2})(?:er)?\s+(?P<m3>[a-z]{3,9})\.?\s+(?P<y3>\d{4})")
_DATE_LABEL = (r"(?:date\s+(?:de\s+(?:la\s+)?)?facture|date\s+d['’]?emission|facture\s+du|facturee?\s+le|emise?\s+le"
               r"|invoice\s+date|date\s+of\s+issue|issued\s+on|date)\s*[:\-]?\s*")
_AMOUNT = r"(-?\d{1,3}(?:[   .,]\d{3})*(?:[.,]\d{1,2})|-?\d+(?:[.,]\d{1,2}))\s*(?:€|eur\b|euros?\b)?"
_AMOUNT_LABELS = (r"net\s+a\s+payer", r"total\s+ttc", r"montant\s+ttc", r"total\s+a\s+payer", r"reste\s+a\s+payer",
                  r"amount\s+due", r"total\s+due", r"balance\s+due", r"total\s+(?:\(?eur\)?|€)", r"total")
_NUMBER = (r"(?:facture|invoice|avoir|credit\s+note)\s*(?:n\s*[°ºo]\.?|num(?:ero)?\.?|number|no\.?|#|ref(?:erence)?\.?)\s*[:\-]?\s*"
           r"([a-z0-9][a-z0-9/_.\-]{0,39})"
           r"|(?:n\s*[°º]\s*(?:de\s+)?facture|numero\s+de\s+facture|invoice\s+(?:number|no\.?|#))\s*[:\-]?\s*([a-z0-9][a-z0-9/_.\-]{0,39})")


def _text_for_search(text: str) -> str:
    """Accents removed and lower case, but same length as the original so positions still match."""
    out = []
    for char in text:
        base = unicodedata.normalize("NFKD", char)
        base = "".join(c for c in base if not unicodedata.combining(c)) or char
        out.append(base[0].casefold() if base else char)
    return "".join(out)


def _date_from(match: re.Match) -> date | None:
    try:
        if match.group("y1"):
            day = date(int(match.group("y1")), int(match.group("m1")), int(match.group("d1")))
        elif match.group("y2"):
            day = date(int(match.group("y2")), int(match.group("m2")), int(match.group("d2")))
        else:
            month = _MONTHS.get(match.group("m3"))
            if not month:
                return None
            day = date(int(match.group("y3")), month, int(match.group("d3")))
    except ValueError:
        return None
    return day if date(2000, 1, 1) <= day <= date(2100, 12, 31) else None


def suggestions(text: str, data: dict[str, Any]) -> dict[str, Any]:
    """What the text of an invoice seems to say. Every value is a proposal to check; absent stays empty."""
    found: dict[str, Any] = {}
    if not text:
        return found
    low = _text_for_search(text)
    # Invoice date: a labelled date first, then the first date of the document.
    labelled = re.search(_DATE_LABEL + r"(?:" + _DATE + r")", low)
    day = _date_from(labelled) if labelled else None
    if day is None:
        for match in re.finditer(_DATE, low):
            day = _date_from(match)
            if day:
                break
    if day:
        found["invoice_date"] = day.isoformat()
    # Amount including tax: the most explicit label wins; its last occurrence (totals come last).
    for label in _AMOUNT_LABELS:
        matches = list(re.finditer(r"\b" + label + r"\b[^0-9\-\n]{0,30}" + _AMOUNT, low))
        for match in reversed(matches):
            try:
                cents = money.parse_amount_text(match.group(1).replace(" ", " ").replace(" ", " "))
            except ValueError:
                cents = None
            if cents and 0 < cents <= 10_000_000_00:
                found["amount"] = cents
                break
        if "amount" in found:
            break
    # Invoice number: a value with at least one digit after « Facture n° », « Invoice # »…
    for match in re.finditer(_NUMBER, low):
        start, end = match.span(1) if match.group(1) else match.span(2)
        value = text[start:end].strip(".-/_")
        if re.search(r"\d", value) and len(value) >= 2:
            found["invoice_number"] = value
            break
    # Supplier: only one the person already created, named in the text. Never guessed from the text alone.
    best: tuple[int, str] | None = None
    for supplier in data.get("suppliers", {}).values():
        if supplier.get("archived"):
            continue
        name = _text_for_search(" ".join(str(supplier.get("name", "")).split()))
        if len(name) < 3:
            continue
        match = re.search(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])", low)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), supplier["id"])
    if best:
        found["supplier_id"] = best[1]
    return found


# --------------------------------------------------------------------------- duplicates

def _supplier_key(data: dict[str, Any], supplier_id: str, supplier: str) -> str:
    if supplier_id and supplier_id in data.get("suppliers", {}):
        return "id:" + supplier_id
    name = normalized(supplier)
    if name:
        for item in data.get("suppliers", {}).values():
            if normalized(item.get("name")) == name:
                return "id:" + item["id"]
        return "name:" + name
    return ""


def duplicates(data: dict[str, Any], lang: str, *, sha: str = "", supplier_id: str = "", supplier: str = "",
               invoice_number: str = "", invoice_date: str = "", amount: int | None = None,
               exclude_entry: str = "", exclude_document: str = "") -> dict[str, list[dict[str, Any]]]:
    """Existing documents and expenses this invoice may duplicate, on every property (DUP 02).

    ``certain``: same file, or same supplier and same invoice number.
    ``probable``: same supplier, date and amount, one of them without a number.
    """
    certain: list[dict[str, Any]] = []
    probable: list[dict[str, Any]] = []
    key = _supplier_key(data, supplier_id, supplier)
    ref = reference(invoice_number)
    entries = data.get("entries", {})
    linked_to_excluded = {d["id"] for d in data.get("documents", {}).values() if exclude_entry and exclude_entry in d.get("entry_ids", [])}
    seen: set[str] = set()

    def row(kind: str, reason: str, doc: dict[str, Any] | None, entry: dict[str, Any] | None) -> dict[str, Any]:
        entry = entry or (entries.get((doc or {}).get("entry_ids", [""])[0]) if doc and doc.get("entry_ids") else None)
        prop = data["properties"].get((entry or doc or {}).get("property_id", ""), {})
        return {
            "reason": reason, "reason_label": REASON_LABELS[reason][0 if lang == "fr" else 1], "kind": kind,
            "document_id": (doc or {}).get("id", ""), "entry_id": (entry or {}).get("id", ""),
            "label": (entry or {}).get("label") or (doc or {}).get("filename", ""),
            "date": (entry or {}).get("date") or (doc or {}).get("invoice_date", ""),
            "amount": (entry or {}).get("amount") if entry else (doc or {}).get("amount"),
            "property_id": prop.get("id", ""), "property": prop.get("name", ""),
            "archived": bool((entry or {}).get("archived")), "superseded": bool((entry or {}).get("superseded_by")),
        }

    for doc in data.get("documents", {}).values():
        if doc["id"] == exclude_document or doc["id"] in linked_to_excluded:
            continue
        if sha and doc.get("sha256") == sha:
            certain.append(row("document", "same_file", doc, None))
            seen.add("d:" + doc["id"])
            continue
        doc_key = _supplier_key(data, doc.get("supplier_id", ""), doc.get("supplier", ""))
        if key and doc_key == key:
            doc_ref = reference(doc.get("invoice_number"))
            if ref and doc_ref == ref:
                certain.append(row("document", "same_reference", doc, None))
                seen.add("d:" + doc["id"])
            elif (invoice_date and amount and doc.get("invoice_date") == invoice_date and doc.get("amount") == amount
                  and not (ref and doc_ref)):
                probable.append(row("document", "same_supplier_date_amount", doc, None))
    linked_entries = {eid for d in data.get("documents", {}).values() if "d:" + d["id"] in seen for eid in d.get("entry_ids", [])}
    for entry in entries.values():
        if entry["id"] == exclude_entry or entry["id"] in linked_entries or entry["kind"] != "expense" or not key:
            continue
        if _supplier_key(data, entry.get("supplier_id", ""), "") != key:
            continue
        number = reference(entry.get("invoice_number"))
        if ref and number == ref:
            certain.append(row("entry", "same_reference", None, entry))
        elif invoice_date and amount and entry["date"] == invoice_date and entry["amount"] == amount and not (ref and number):
            probable.append(row("entry", "same_supplier_date_amount", None, entry))
    return {"certain": certain, "probable": probable}


REASON_LABELS = {
    "same_file": ("même fichier, déjà enregistré", "same file, already stored"),
    "same_reference": ("même prestataire et même numéro de facture", "same supplier and same invoice number"),
    "same_supplier_date_amount": ("même prestataire, même date et même montant", "same supplier, same date and same amount"),
}


# --------------------------------------------------------------------------- views

def incomplete(doc: dict[str, Any]) -> bool:
    """Listed in « À vérifier » until attached to an expense and described (supplier and amount)."""
    return not doc.get("entry_ids") or doc.get("amount") is None or not (doc.get("supplier") or doc.get("supplier_id"))


def summary(data: dict[str, Any], doc: dict[str, Any], lang: str) -> dict[str, Any]:
    entries = data.get("entries", {})
    linked = [entries[eid] for eid in doc.get("entry_ids", []) if eid in entries]
    supplier = data.get("suppliers", {}).get(doc.get("supplier_id") or "", {})
    return {
        "id": doc["id"], "property_id": doc["property_id"], "property": data["properties"].get(doc["property_id"], {}).get("name", "—"),
        "filename": doc.get("filename", ""), "size": doc.get("size", 0), "pages": doc.get("pages", 0), "sha256": doc.get("sha256", ""),
        "text_found": bool(doc.get("text_found")),
        "supplier_id": doc.get("supplier_id", ""), "supplier": supplier.get("name") or doc.get("supplier", ""),
        "invoice_number": doc.get("invoice_number", ""), "invoice_date": doc.get("invoice_date", ""), "amount": doc.get("amount"),
        "entries": [{"id": e["id"], "label": e["label"], "date": e["date"], "amount": e["amount"], "kind": e["kind"],
                     "category": category_label(data["categories"].get(e["category_id"]), lang),
                     "archived": bool(e.get("archived")), "superseded": bool(e.get("superseded_by"))} for e in linked],
        "incomplete": incomplete(doc),
        "created_at": doc.get("created_at"), "revision": int(doc.get("revision") or 0), "updated_at": doc.get("updated_at"),
    }


def matches(item: dict[str, Any], query: str) -> bool:
    words = normalized(query).split()
    haystack = normalized(" ".join(str(item.get(k) or "") for k in ("filename", "supplier", "invoice_number", "property"))
                          + " " + " ".join(e["label"] for e in item["entries"]))
    return all(word in haystack for word in words)


# --------------------------------------------------------------------------- sample PDFs (demo, tests)

def sample_pdf(lines: list[str], *, title: str = "Facture") -> bytes:
    """A small, valid, text PDF (one page, Helvetica, Windows-1252), always the same bytes for the same lines."""
    def escape(text: str) -> bytes:
        raw = text.encode("cp1252", "replace")
        return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")

    stream = b"BT /F1 12 Tf 56 780 Td 16 TL\n" + b"".join(b"(" + escape(line) + b") Tj T*\n" for line in lines) + b"ET\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream",
        b"<< /Title (" + escape(title) + b") /Producer (Rental Cockpit) >>",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n0000000000 65535 f \n"
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R /Info 6 0 R >>\nstartxref\n"
    out += str(xref).encode() + b"\n%%EOF\n"
    return bytes(out)


SAMPLES = {
    "demo-invoice-018": lambda: sample_pdf([
        "Prestataire Démo — document fictif",
        "Facture n° F-DEMO-018",
        "Bien : Appartement A (fictif)",
        "",
        "Ménage                       100,00 €",
        "Linge : 4 lots × 10,00 €      40,00 €",
        "Déplacement                   10,00 €",
        "",
        "Total TTC                    150,00 €",
    ], title="Facture F-DEMO-018 (fictive)"),
}
