"""DICOM Structured Report (SR) export for QA documentation.

Writes a DICOM Comprehensive SR that documents the result of a film QA
comparison — the dosimetry method, gamma analysis (criteria, pass rate, points
evaluated/passed), and dose statistics — so a measurement can be archived in
the patient's imaging study in a standards-compliant, queryable form rather
than as a loose PDF.

The concept names use a private coding scheme (``99CHRMDOSE``); measurement
units use UCUM. A companion :func:`read_dicom_sr` reads the document back into a
flat dict, which is mainly useful for verification and round-tripping.

Requires the optional `pydicom` dependency:
    pip install chromadose[dicom]
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydicom.dataset import Dataset

    from chromadose.analysis.gamma import GammaResult

# DICOM SOP Class UID for Comprehensive SR Storage.
_COMPREHENSIVE_SR_SOP_CLASS_UID = "1.2.840.10008.5.1.4.1.1.88.33"

# Private coding scheme designator for chromadose-specific concept names.
_SCHEME = "99CHRMDOSE"


def _import_error() -> ImportError:
    return ImportError(
        "pydicom is required for DICOM SR export. "
        "Install with: pip install chromadose[dicom]"
    )


def _code(value: str, scheme: str, meaning: str) -> Dataset:
    """Build a coded-concept Dataset (CodeValue / scheme / CodeMeaning)."""
    from pydicom.dataset import Dataset

    ds = Dataset()
    ds.CodeValue = value
    ds.CodingSchemeDesignator = scheme
    ds.CodeMeaning = meaning
    return ds


def _text_item(concept_value: str, concept_meaning: str, text: str) -> Dataset:
    """Build a TEXT content item."""
    from pydicom.dataset import Dataset

    item = Dataset()
    item.RelationshipType = "CONTAINS"
    item.ValueType = "TEXT"
    item.ConceptNameCodeSequence = [_code(concept_value, _SCHEME, concept_meaning)]
    item.TextValue = text
    return item


def _num_item(
    concept_value: str,
    concept_meaning: str,
    value: float,
    unit_value: str,
    unit_meaning: str,
) -> Dataset:
    """Build a NUM (numeric measurement) content item with UCUM units."""
    from pydicom.dataset import Dataset

    item = Dataset()
    item.RelationshipType = "CONTAINS"
    item.ValueType = "NUM"
    item.ConceptNameCodeSequence = [_code(concept_value, _SCHEME, concept_meaning)]
    measured = Dataset()
    measured.NumericValue = float(value)
    measured.MeasurementUnitsCodeSequence = [_code(unit_value, "UCUM", unit_meaning)]
    item.MeasuredValueSequence = [measured]
    return item


def _container(concept_value: str, concept_meaning: str, children: list[Dataset]) -> Dataset:
    """Build a CONTAINER content item holding child items."""
    from pydicom.dataset import Dataset

    item = Dataset()
    item.RelationshipType = "CONTAINS"
    item.ValueType = "CONTAINER"
    item.ConceptNameCodeSequence = [_code(concept_value, _SCHEME, concept_meaning)]
    item.ContinuityOfContent = "SEPARATE"
    item.ContentSequence = children
    return item


def save_dicom_sr(
    path: str | Path,
    *,
    gamma_result: GammaResult | None = None,
    max_dose_gy: float | None = None,
    mean_dose_gy: float | None = None,
    method: str = "",
    film_type: str = "",
    patient_name: str = "",
    patient_id: str = "",
    plan_label: str = "",
    content_datetime: datetime | None = None,
) -> None:
    """Write a film QA result to a DICOM Comprehensive SR file.

    Parameters:
        path: Output path for the DICOM SR file.
        gamma_result: Gamma analysis result to document (criteria, pass rate,
            points evaluated/passed, dose threshold). Omit to skip the gamma
            section.
        max_dose_gy: Maximum measured dose in Gy, recorded if provided.
        mean_dose_gy: Mean measured dose in Gy, recorded if provided.
        method: Dosimetry method name (e.g. "micke").
        film_type: Film model (e.g. "EBT3"), recorded if provided.
        patient_name: Patient name for the DICOM header.
        patient_id: Patient ID for the DICOM header.
        plan_label: RT Plan label, recorded if provided.
        content_datetime: Content date/time for the document. Defaults to now.

    Raises:
        ImportError: If pydicom is not installed.
    """
    try:
        from pydicom.dataset import Dataset, FileMetaDataset
        from pydicom.uid import UID, ExplicitVRLittleEndian, generate_uid
    except ImportError:
        raise _import_error()

    when = content_datetime or datetime.now()

    children: list[Dataset] = []
    if method:
        children.append(_text_item("CD001", "Dosimetry method", method))
    if film_type:
        children.append(_text_item("CD002", "Film type", film_type))
    if plan_label:
        children.append(_text_item("CD003", "RT Plan label", plan_label))

    if gamma_result is not None:
        children.append(
            _container(
                "CD019",
                "Gamma analysis",
                [
                    _text_item("CD010", "Gamma criteria", gamma_result.criteria),
                    _num_item(
                        "CD011", "Gamma pass rate",
                        float(gamma_result.pass_rate) * 100.0, "%", "percent",
                    ),
                    _num_item(
                        "CD012", "Points evaluated",
                        float(gamma_result.points_evaluated), "1", "no units",
                    ),
                    _num_item(
                        "CD013", "Points passed",
                        float(gamma_result.points_passed), "1", "no units",
                    ),
                    _num_item(
                        "CD014", "Dose threshold",
                        float(gamma_result.dose_threshold_pct), "%", "percent",
                    ),
                ],
            )
        )

    dose_children: list[Dataset] = []
    if max_dose_gy is not None:
        dose_children.append(_num_item("CD020", "Maximum dose", float(max_dose_gy), "Gy", "Gray"))
    if mean_dose_gy is not None:
        dose_children.append(_num_item("CD021", "Mean dose", float(mean_dose_gy), "Gy", "Gray"))
    if dose_children:
        children.append(_container("CD029", "Dose statistics", dose_children))

    sop_class_uid = UID(_COMPREHENSIVE_SR_SOP_CLASS_UID)
    sop_instance_uid = generate_uid()

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = sop_class_uid
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta
    ds.SOPClassUID = sop_class_uid
    ds.SOPInstanceUID = sop_instance_uid

    # Patient / Study / Series
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.Modality = "SR"
    ds.Manufacturer = "chromadose"
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    if plan_label:
        ds.RTPlanLabel = plan_label

    # SR Document General module
    ds.ContentDate = when.strftime("%Y%m%d")
    ds.ContentTime = when.strftime("%H%M%S")
    ds.CompletionFlag = "COMPLETE"
    ds.VerificationFlag = "UNVERIFIED"

    # Root content item (the document is itself a CONTAINER)
    ds.ValueType = "CONTAINER"
    ds.ConceptNameCodeSequence = [_code("CD000", _SCHEME, "Radiochromic film QA report")]
    ds.ContinuityOfContent = "SEPARATE"
    ds.ContentSequence = children

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # The keyword that enforces a compliant file was renamed in pydicom 3.0
    # (write_like_original -> enforce_file_format); support both.
    try:
        ds.save_as(str(out), enforce_file_format=True)
    except TypeError:
        ds.save_as(str(out), write_like_original=False)


def read_dicom_sr(path: str | Path) -> dict[str, Any]:
    """Read a chromadose QA SR into a flat ``{concept meaning: value}`` dict.

    TEXT items map to their string value and NUM items to their numeric value
    (as a float). Nested containers are flattened. This is primarily intended
    for verification and round-tripping, not general SR parsing.

    Raises:
        ImportError: If pydicom is not installed.
    """
    try:
        import pydicom
    except ImportError:
        raise _import_error()

    ds = pydicom.dcmread(str(Path(path)))
    result: dict[str, Any] = {}

    def walk(items: list[Dataset]) -> None:
        for item in items:
            name = ""
            concept = getattr(item, "ConceptNameCodeSequence", None)
            if concept:
                name = str(concept[0].CodeMeaning)
            value_type = getattr(item, "ValueType", "")
            if value_type == "TEXT":
                result[name] = str(item.TextValue)
            elif value_type == "NUM":
                measured = getattr(item, "MeasuredValueSequence", None)
                if measured:
                    result[name] = float(measured[0].NumericValue)
            if "ContentSequence" in item:
                walk(item.ContentSequence)

    if "ContentSequence" in ds:
        walk(ds.ContentSequence)
    return result
