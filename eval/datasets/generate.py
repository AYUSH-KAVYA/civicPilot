import json
from pathlib import Path


OUT = Path(__file__).with_name("grievances.json")
DEPARTMENTS = ("roads", "water", "sanitation", "electricity", "parks", "public_health")
URGENCIES = ("low", "medium", "high", "critical")
DISRUPTIONS = ("none", "ticket_rejection", "crew_no_show", "new_evidence", "duplicate_cluster", "dispute")

templates = [
    ("roads", "A deep pothole is blocking the main road near Bus Stop 12.", "medium"),
    ("water", "A burst water pipe is flooding the school entrance.", "critical"),
    ("sanitation", "Garbage has piled up outside the market for three days.", "medium"),
    ("electricity", "A live wire has fallen near the children's school.", "critical"),
    ("parks", "A large tree is leaning over the hospital boundary.", "critical"),
    ("public_health", "Standing water and mosquitoes are reported near clinic block.", "high"),
]
vague = [
    "There is a problem here.",
    "Please help.",
    "It is broken.",
    "Something is leaking.",
    "Too much garbage.",
    "The road is bad.",
    "No power.",
    "Help near the place.",
    "Tree fell.",
    "It is unsafe.",
]

cases = []
for i in range(60):
    if i < 10:
        text = vague[i]
        department = DEPARTMENTS[i % len(DEPARTMENTS)]
        urgency = "low" if i % 3 else "medium"
    elif i < 20:
        anchor = i - 10
        department, text, urgency = templates[anchor % len(templates)]
        text = f"Duplicate report {anchor + 1}: " + text
        urgency = "high" if urgency == "critical" else urgency
    elif i >= 50:
        multilingual = [
            ("roads", "बड़े गड्ढे के कारण स्कूल के पास सड़क बंद है।", "high"),
            ("water", "Main ke paas paani ka pipe leak ho raha hai.", "high"),
            ("sanitation", "La calle está llena de basura cerca del mercado.", "medium"),
            ("electricity", "Taliye ki taar gir gayi hai aur sparks ho rahe hain.", "critical"),
            ("parks", "Un grand arbre est tombé près de l'hôpital.", "critical"),
            ("public_health", "उद्यान में मच्छरों का प्रजनन हो रहा है।", "high"),
        ]
        department, text, urgency = multilingual[(i - 50) % len(multilingual)]
    else:
        department, text, urgency = templates[(i - 20) % len(templates)]

    disruption = DISRUPTIONS[(i // 10) % len(DISRUPTIONS)]
    if i < 10:
        disruption = "none"
    if i >= 50:
        disruption = "new_evidence" if i % 2 else "dispute"
    lat = 28.6139 + (i % 10) * 0.0002
    lng = 77.2090 + (i % 10) * 0.0003
    cases.append({
        "id": f"SIM-{i + 1:04d}",
        "text": text,
        "language": "en",
        "lat": lat,
        "lng": lng,
        "address": f"Sector {i % 10 + 1}, Civic Ward {i % 6 + 1}",
        "true_department": department,
        "true_urgency": urgency,
        "human_needed": urgency == "critical" or disruption in ("dispute", "duplicate_cluster"),
        "disruption": disruption,
        "simulated": True,
    })

OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {len(cases)} simulated grievances to {OUT}")
