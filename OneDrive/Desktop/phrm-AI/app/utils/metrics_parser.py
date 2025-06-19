import re

# Define metrics and regex patterns
METRIC_PATTERNS = {
    "glucose": r"(glucose|blood sugar)[^\d]*(\d+\.?\d*)\s*(mg/dl|mg per dL)?",
    "hemoglobin": r"(hemoglobin)[^\d]*(\d+\.?\d*)\s*(g/dl|g per dL)?",
    "crp": r"(crp|C-reactive protein)[^\d]*(\d+\.?\d*)\s*(mg/l|mg per L)?",
}

def extract_metrics(text: str) -> list:
    results = []
    for metric, pattern in METRIC_PATTERNS.items():
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            value = float(match[1])
            unit = match[2].strip() if match[2] else None
            results.append({
                "metric": metric,
                "value": value,
                "unit": unit
            })
    return results