import numpy as np
from bom_app.models import Item, BOM, BOMLine, RoutingStep
from bom_app.views import collect_routing_data

# --- Monte-Carlo driver: representative task times & error likelihoods -----------
# Units: seconds for time, dimensionless probability for errors
# -------------------------------------------------------------------------------

PROCESS_STEPS = {
    "cad_interpretation_time_per_component": {"mean": 7.5, "std": 3.0},      # minutes :contentReference[oaicite:8]{index=8}
    "manual_data_entry_time_per_item":      {"mean": 60,  "std": 15},       # seconds :contentReference[oaicite:9]{index=9}
    "manual_interactions_per_item":         {"mean": 4,   "std": 1},        # fields/clicks :contentReference[oaicite:10]{index=10}
    "error_probability_per_manual_step":    {"mean": 0.03, "range": (0.021, 0.052)},  # probability :contentReference[oaicite:11]{index=11}
    "quote_compilation_time":               {"mean": 30,  "std": 60}        # minutes :contentReference[oaicite:12]{index=12}
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
    
    data = collect_routing_data(bom.parent)

    for _ in range(trials):
        total_time = 0
        total_entries = 0
        errors = []

        # --- Step 1: CAD interpretation (for the part) ---

        # Simulate CAD interpretation for each part and assembly in data
        
        overall_simulation = simulate_cad_interpretation()
        total_time += overall_simulation["step_time"]
        total_entries += overall_simulation["interactions"]
        errors.extend(overall_simulation["errors"])

        for line in data["children"]:
            # Simulate CAD interpretation for each component
            component_simulation = simulate_cad_interpretation()
            total_time += component_simulation["step_time"]
            total_entries += component_simulation["interactions"]
            errors.extend(component_simulation["errors"])

            if len(line["children"]) > 0:
                # Recursively process children
                for child in line["children"]:
                    child_simulation = simulate_cad_interpretation()
                    total_time += child_simulation["step_time"]
                    total_entries += child_simulation["interactions"]
                    errors.extend(child_simulation["errors"])

                    if len(child["children"]) > 0:
                        # Recursively process grandchildren
                        for grandchild in child["children"]:
                            grandchild_simulation = simulate_cad_interpretation()
                            total_time += grandchild_simulation["step_time"]
                            total_entries += grandchild_simulation["interactions"]
                            errors.extend(grandchild_simulation["errors"])

        # --- Step 2: Enter into costing sheets (simulate routing steps) ---

        overall_simulation = simulate_wc_calculations(data["work_centers"])
        total_time += overall_simulation["step_time"]
        total_entries += overall_simulation["interactions"] + 2  # +2 for the two manual entries in the costing sheet
        errors.extend(overall_simulation["errors"])

        for line in data["children"]:
            # Simulate CAD interpretation for each component
            component_simulation = simulate_wc_calculations(data["work_centers"])
            total_time += component_simulation["step_time"]
            total_entries += component_simulation["interactions"] + 2  # +2 for the two manual entries in the costing sheet
            errors.extend(component_simulation["errors"])

            if len(line["children"]) > 0:
                # Recursively process children
                for child in line["children"]:
                    child_simulation = simulate_wc_calculations(data["work_centers"])
                    total_time += child_simulation["step_time"]
                    total_entries += child_simulation["interactions"] + 2  # +2 for the two manual entries in the costing sheet
                    errors.extend(child_simulation["errors"])

                    if len(child["children"]) > 0:
                        # Recursively process grandchildren
                        for grandchild in child["children"]:
                            grandchild_simulation = simulate_wc_calculations(data["work_centers"])
                            total_time += grandchild_simulation["step_time"]
                            total_entries += grandchild_simulation["interactions"] + 2  # +2 for the two manual entries in the costing sheet
                            errors.extend(grandchild_simulation["errors"])

        # --- Step 3: Internal software entry ---
        # Simulate quote compilation time
        step_entries = 0
        step_entries += 2
        
        for line in data["children"]:
            # Simulate CAD interpretation for each component
            step_entries +=  2  # +2 for the two manual entries in the costing sheet

            if len(line["children"]) > 0:
                # Recursively process children
                for child in line["children"]:
                    step_entries +=  2  

                    if len(child["children"]) > 0:
                        # Recursively process grandchildren
                        for grandchild in child["children"]:
                            step_entries += 2

        counter = 0
        while counter < step_entries:
            if np.random.uniform(0, 1) < np.random.uniform(
                PROCESS_STEPS["error_probability_per_manual_step"]["range"][0],
                PROCESS_STEPS["error_probability_per_manual_step"]["range"][1]
            ):
                errors.append(f"Error in manual entry {counter} for item")
                # 50/50 if error is detected or not
                if np.random.uniform(0, 1) < 0.5:
                    step_entries += 1
            counter += 1
        total_time += step_entries * PROCESS_STEPS["manual_data_entry_time_per_item"]["std"]

        quote_time = np.random.normal(
            PROCESS_STEPS["quote_compilation_time"]["mean"],
            PROCESS_STEPS["quote_compilation_time"]["std"]
        ) * 60
        total_time += quote_time

        results.append({
            "total_time_sec": round(total_time, 2),
            "manual_entries": total_entries,
            "error_count": len(errors),
            "error_details": errors
        })
    return results


def simulate_cad_interpretation():
    errors = []
    step_time = np.random.normal(
        PROCESS_STEPS["cad_interpretation_time_per_component"]["mean"],
        PROCESS_STEPS["cad_interpretation_time_per_component"]["std"]
    ) * 60
    step_interactions = np.random.normal(
        PROCESS_STEPS["manual_interactions_per_item"]["mean"],
        PROCESS_STEPS["manual_interactions_per_item"]["std"]
    )
    counter = 0
    while  counter < step_interactions:
        if np.random.uniform(0, 1) < np.random.uniform(
            PROCESS_STEPS["error_probability_per_manual_step"]["range"][0],
            PROCESS_STEPS["error_probability_per_manual_step"]["range"][1]
        ):
            errors.append(f"Error in manual entry {counter} for item")
            # 50/50 if error is detected or not
            if np.random.uniform(0, 1) < 0.5:
                step_interactions += 1
        counter += 1
    step_time += step_interactions * PROCESS_STEPS["manual_data_entry_time_per_item"]["mean"]
    return {"step_time": step_time, "errors": errors, "interactions": step_interactions}


def simulate_wc_calculations(routing_steps):
    step_time = 0
    step_interactions = 0
    errors = []
    for key, value in routing_steps.items():
        if value == 0:
            continue
        step_interactions = np.random.normal(
            PROCESS_STEPS["manual_interactions_per_item"]["mean"],
            PROCESS_STEPS["manual_interactions_per_item"]["std"]
        )
        counter = 0
        while counter < step_interactions:
            if np.random.uniform(0, 1) < np.random.uniform(
                PROCESS_STEPS["error_probability_per_manual_step"]["range"][0],
                PROCESS_STEPS["error_probability_per_manual_step"]["range"][1]
            ):
                errors.append(f"Error in manual entry {counter} for item")
                # 50/50 if error is detected or not
                if np.random.uniform(0, 1) < 0.5:
                    step_interactions += 1
            counter += 1
        step_time += step_interactions * np.random.normal(
            PROCESS_STEPS["manual_data_entry_time_per_item"]["mean"],
            PROCESS_STEPS["manual_data_entry_time_per_item"]["std"]
        )

    return {
        "step_time": step_time,
        "errors": errors,
        "interactions": step_interactions
    }