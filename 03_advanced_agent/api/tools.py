"""Helper utilities: ICD-10 fallback lookup and SOAP note formatter."""

# ---------------------------------------------------------------------------
# ICD-10-CM fallback lookup
# ---------------------------------------------------------------------------

_ICD10_FALLBACK: dict[str, str] = {
    "hypertension": "I10",
    "type 2 diabetes": "E11.9",
    "diabetes": "E11.9",
    "heart failure": "I50.9",
    "atrial fibrillation": "I48.91",
    "stroke": "I63.9",
    "myocardial infarction": "I21.9",
    "coronary artery disease": "I25.10",
    "asthma": "J45.909",
    "copd": "J44.1",
    "pneumonia": "J18.9",
    "pulmonary embolism": "I26.99",
    "deep vein thrombosis": "I82.409",
    "hypothyroidism": "E03.9",
    "hyperthyroidism": "E05.90",
    "hyperlipidemia": "E78.5",
    "obesity": "E66.9",
    "chronic kidney disease": "N18.9",
    "acute kidney injury": "N17.9",
    "anemia": "D64.9",
    "sepsis": "A41.9",
    "urinary tract infection": "N39.0",
    "depression": "F32.9",
    "anxiety": "F41.9",
    "dementia": "F03.90",
    "epilepsy": "G40.909",
    "migraine": "G43.909",
    "osteoporosis": "M81.0",
    "rheumatoid arthritis": "M06.9",
    "osteoarthritis": "M19.90",
    "gerd": "K21.0",
    "peptic ulcer": "K27.9",
    "liver cirrhosis": "K74.60",
    "hepatitis": "K75.9",
    "cancer": "C80.1",
    "lung cancer": "C34.90",
    "breast cancer": "C50.919",
    "prostate cancer": "C61",
    "colon cancer": "C18.9",
}


def get_icd10_code(condition: str) -> str:
    """Return an ICD-10-CM code for a condition string (case-insensitive fallback lookup)."""
    key = condition.lower().strip()
    for term, code in _ICD10_FALLBACK.items():
        if term in key or key in term:
            return code
    return "Z99.89"  # generic fallback: dependence on enabling machines / NOS


# ---------------------------------------------------------------------------
# SOAP note formatter
# ---------------------------------------------------------------------------

def format_soap_template(
    subjective: str,
    objective: str,
    assessment: str,
    plan: str,
) -> str:
    """Return a formatted markdown SOAP note string."""
    return (
        f"**S (Subjective):**\n{subjective.strip()}\n\n"
        f"**O (Objective):**\n{objective.strip()}\n\n"
        f"**A (Assessment):**\n{assessment.strip()}\n\n"
        f"**P (Plan):**\n{plan.strip()}"
    )
