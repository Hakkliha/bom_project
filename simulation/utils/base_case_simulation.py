import numpy as np
from bom_app.models import Item, BOM, BOMLine, RoutingStep

# Simulation settings
PROCESS_STEPS = {
    "cad_interpretation_time": (180, 30),   # (mean, std) in seconds
    "workstation_entry_time": (60, 15),     # per workstation
    "aggregation_time": (90, 20),           # final costing
    "internal_sw_entry_time": (45, 10),
    "entry_clicks": 8,
    "error_probs": {
        "cad": 0.02,       # interpreting CAD models
        "workstation": 0.05,
        "aggregation": 0.03,
        "internal_entry": 0.01,
    }
}

def simulate_quote_for_item(item: Item, trials=100):
    results = []

    # Only simulate for assemblies
    if item.item_type != 'A':
        return results

    # Fetch associated BOM and Routing
    bom = item.booms.first()
    if not bom:
        return results

    for _ in range(trials):
        total_time = 0
        total_entries = 0
        errors = []

        # --- Step 1: CAD interpretation (for the product) ---
        total_time += np.random.normal(*PROCESS_STEPS["cad_interpretation_time"])
        if np.random.rand() < PROCESS_STEPS["error_probs"]["cad"]:
            errors.append("cad_interpretation")

        # --- Step 2: For each BOMLine component ---
        for line in bom.lines.all():
            total_time += np.random.normal(*PROCESS_STEPS["cad_interpretation_time"])
            total_entries += PROCESS_STEPS["entry_clicks"]
            if np.random.rand() < PROCESS_STEPS["error_probs"]["cad"]:
                errors.append(f"cad_interpretation_component_{line.component.item_no}")

        # --- Step 3: Enter into costing sheets (simulate routing steps) ---
        routing_steps = bom.routing.all()
        for step in routing_steps:
            total_time += np.random.normal(*PROCESS_STEPS["workstation_entry_time"])
            total_entries += PROCESS_STEPS["entry_clicks"]
            if np.random.rand() < PROCESS_STEPS["error_probs"]["workstation"]:
                errors.append(f"workstation_entry_{step.wc.name}")

        # --- Step 4: Aggregation step ---
        total_time += np.random.normal(*PROCESS_STEPS["aggregation_time"])
        total_entries += PROCESS_STEPS["entry_clicks"]
        if np.random.rand() < PROCESS_STEPS["error_probs"]["aggregation"]:
            errors.append("aggregation_step")

        # --- Step 5: Internal software entry ---
        total_time += np.random.normal(*PROCESS_STEPS["internal_sw_entry_time"])
        total_entries += PROCESS_STEPS["entry_clicks"]
        if np.random.rand() < PROCESS_STEPS["error_probs"]["internal_entry"]:
            errors.append("internal_sw_entry")

        results.append({
            "item_id": item.id,
            "item_no": item.item_no,
            "item_desc": item.description,
            "total_time_sec": round(total_time, 2),
            "manual_entries": total_entries,
            "error_count": len(errors),
            "error_details": errors
        })
    return results
