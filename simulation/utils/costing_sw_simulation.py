import numpy as np
from bom_app.models import Item, BOM, BOMLine, RoutingStep
from bom_app.views import collect_routing_data
from .base_case_simulation import PROCESS_STEPS, simulate_cad_interpretation


def simulate_quote_for_item_sw(item: Item, trials=100):
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

        # --- Step 2: Enter into costing software (simulate routing steps) ---

        overall_simulation = simulate_wc_calculations(data["work_centers"])
        total_time += overall_simulation["step_time"]
        total_entries += overall_simulation["interactions"] 
        errors.extend(overall_simulation["errors"])

        for line in data["children"]:
            # Simulate CAD interpretation for each component
            component_simulation = simulate_wc_calculations(data["work_centers"])
            total_time += component_simulation["step_time"]
            total_entries += component_simulation["interactions"]
            errors.extend(component_simulation["errors"])

            if len(line["children"]) > 0:
                # Recursively process children
                for child in line["children"]:
                    child_simulation = simulate_wc_calculations(data["work_centers"])
                    total_time += child_simulation["step_time"]
                    total_entries += child_simulation["interactions"] 
                    errors.extend(child_simulation["errors"])

                    if len(child["children"]) > 0:
                        # Recursively process grandchildren
                        for grandchild in child["children"]:
                            grandchild_simulation = simulate_wc_calculations(data["work_centers"])
                            total_time += grandchild_simulation["step_time"]
                            total_entries += grandchild_simulation["interactions"]
                            errors.extend(grandchild_simulation["errors"])

        results.append({
            "total_time_sec": round(total_time, 2),
            "manual_entries": total_entries,
            "error_count": len(errors),
            "error_details": errors
        })
    return results

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
            if np.random.uniform(0, 1) < PROCESS_STEPS["error_probability_per_manual_step"]["range"][0]:
                errors.append(f"Error in manual entry {counter} for item")
                # 50/50 if error is detected or not
                if np.random.uniform(0, 1) < 0.5:
                    step_interactions += 1
            counter += 1
        step_time += step_interactions * PROCESS_STEPS["manual_data_entry_time_per_item"]["std"]

    return {
        "step_time": step_time,
        "errors": errors,
        "interactions": step_interactions
    }