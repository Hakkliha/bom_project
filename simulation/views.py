import json
import time
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from bom_app.models import Item, BOM, BOMLine, WorkCenter, RoutingStep
from simulation.utils.base_case_simulation import simulate_quote_for_item
from simulation.utils.costing_sw_simulation import simulate_quote_for_item_sw
import numpy as np
import random
from django.db.models import Q
from bom_app.views import collect_routing_data, retrieve_top_level_item, build_tree, collect_routing_data_alternative

BATCH_SIZE = 100  # safe limit for SQLite; adjust if using Postgres

def chunked_item_query(item_nos):
    """
    Returns a queryset union for a large IN query
    """
    item_nos = list(item_nos)
    queries = [Q(item_no__in=item_nos[i:i+BATCH_SIZE]) for i in range(0, len(item_nos), BATCH_SIZE)]
    if not queries:
        return Item.objects.none()
    
    q_total = queries[0]
    for q in queries[1:]:
        q_total |= q
    
    return Item.objects.filter(q_total)


@api_view(['GET'])
def simulate_base_case_test(request):
    # Get a random top-level assembly
    chosen_item_no = retrieve_top_level_item(complexity='complex')
    if not chosen_item_no:
        return Response({"error": "No top-level assemblies found."}, status=404)
    
    bom_obj = BOM.objects.get(parent__item_no=chosen_item_no)
    
    tree = build_tree(bom_obj.parent.item_no)
    
    # Get all work centers for column headers
    work_centers = WorkCenter.objects.all().order_by('wc_no')
    
    # Get routing data
    routing_data = collect_routing_data_alternative(bom_obj.parent.item_no)

    return Response(routing_data)




@api_view(['GET'])
def simulate_all_top_level_base_case(request):
    """
    Simulate quoting process for all top-level assemblies in the system
    """
    # Step 1: Get all assemblies that are parents in BOMs
    parent_assemblies = BOM.objects.filter(
        parent__item_type='A'
    ).values_list('parent__item_no', flat=True)

    # Step 2: Exclude any assembly that appears as a component
    sub_assemblies = BOMLine.objects.filter(
        component__item_type='A'
    ).values_list('component__item_no', flat=True)

    top_level_item_nos = set(parent_assemblies) - set(sub_assemblies)
    # Safer filtering in Python to avoid hitting SQL variable limits
    all_assemblies = Item.objects.filter(item_type='A').select_related()
    top_items = [item for item in all_assemblies if item.item_no in top_level_item_nos]


    if not top_items:
        return Response({"error": "No top-level assemblies found."}, status=404)

    overall_results = []
    per_item_summary = []

    for item in top_items:
        simulations = simulate_quote_for_item(item, trials=50)
        if simulations:
            overall_results.extend(simulations)
            per_item_summary.append({
                "item_no": item.item_no,
                "description": item.description,
                "avg_time_sec": round(np.mean([r["total_time_sec"] for r in simulations]), 2),
                "avg_entries": round(np.mean([r["manual_entries"] for r in simulations]), 2),
                "avg_errors": round(np.mean([r["error_count"] for r in simulations]), 2),
            })

    overall_stats = {
        "total_items_simulated": len(per_item_summary),
        "overall_avg_time_sec": round(np.mean([r["total_time_sec"] for r in overall_results]), 2),
        "overall_avg_entries": round(np.mean([r["manual_entries"] for r in overall_results]), 2),
        "overall_avg_errors": round(np.mean([r["error_count"] for r in overall_results]), 2),
    }

    #save results and summary to file
    unique_id = str(int(time.time()))
    with open(f"base_case_simulation_results_{unique_id}.json", "w") as f:
        json.dump({
            "overall_stats": overall_stats,
            "per_item_summary": per_item_summary,
            "overall_results": overall_results,
        }, f, indent=4)

    return Response({
        "summary": overall_stats,})


@api_view(['GET'])
def simulate_base_case_from_complexity(request, complexity):
    """
    Simulate quote process for one random top-level assembly of the given complexity
    """
    # STEP 1: Find all parent assemblies for given complexity
    parent_assemblies = BOM.objects.filter(
        complexity=complexity, 
        parent__item_type='A'
    ).values_list('parent__item_no', flat=True)

    # STEP 2: Exclude assemblies used as components (only top-level)
    sub_assemblies = BOMLine.objects.filter(
        component__item_type='A'
    ).values_list('component__item_no', flat=True)

    top_level_item_nos = set(parent_assemblies) - set(sub_assemblies)

    if not top_level_item_nos:
        return Response({"error": f"No top-level assemblies found with complexity '{complexity}'"}, status=404)

    # STEP 3: Pick a random top-level assembly and simulate
    chosen_item_no = random.choice(list(top_level_item_nos))
    item = Item.objects.get(item_no=chosen_item_no)
    simulations = simulate_quote_for_item(item, trials=50)

    # STEP 4: Summarize results
    avg_time = round(sum(r["total_time_sec"] for r in simulations) / len(simulations), 2)
    avg_errors = round(sum(r["error_count"] for r in simulations) / len(simulations), 2)
    avg_entries = round(sum(r["manual_entries"] for r in simulations) / len(simulations), 2)

    return Response({
        "item": item.item_no,
        "description": item.description,
        "complexity": complexity,
        "avg_time_sec": avg_time,
        "avg_manual_entries": avg_entries,
        "avg_error_count": avg_errors,
        "samples": simulations[:5],  # show just a few sample simulations
    })


def simulate_base_case_template_view(request, complexity):
    # Same logic as above, but rendered via template
    parent_assemblies = BOM.objects.filter(
        complexity=complexity, 
        parent__item_type='A'
    ).values_list('parent__item_no', flat=True)

    sub_assemblies = BOMLine.objects.filter(
        component__item_type='A'
    ).values_list('component__item_no', flat=True)

    top_level_item_nos = set(parent_assemblies) - set(sub_assemblies)
    if not top_level_item_nos:
        return render(request, "simulation/no_results.html", {"complexity": complexity})

    chosen_item_no = random.choice(list(top_level_item_nos))
    item = Item.objects.get(item_no=chosen_item_no)
    simulations = simulate_quote_for_item(item, trials=50)

    context = {
        "item": item,
        "complexity": complexity,
        "avg_time": round(sum(r["total_time_sec"] for r in simulations) / len(simulations), 2),
        "avg_errors": round(sum(r["error_count"] for r in simulations) / len(simulations), 2),
        "avg_entries": round(sum(r["manual_entries"] for r in simulations) / len(simulations), 2),
        "results": simulations[:5],
    }
    return render(request, "simulation/results.html", context)

@api_view(['GET'])
def simulate_top_level_by_complexity(request, complexity):
    """
    Simulate quoting process for all top-level assemblies with given complexity
    """
    # STEP 1: Get item_nos for assemblies used as BOM parents (with matching complexity)
    parent_assemblies = BOM.objects.filter(
        complexity=complexity,
        parent__item_type='A'
    ).values_list('parent__item_no', flat=True)

    # STEP 2: Get item_nos of assemblies used as components in BOMLines
    sub_assemblies = BOMLine.objects.filter(
        component__item_type='A'
    ).values_list('component__item_no', flat=True)

    # STEP 3: Find top-level item_nos (parent but not sub-assembly)
    top_level_item_nos = set(parent_assemblies) - set(sub_assemblies)

    # STEP 4: Retrieve Items in Python to avoid SQL variable limit
    all_assemblies = Item.objects.filter(item_type='A')
    top_items = [item for item in all_assemblies if item.item_no in top_level_item_nos]

    if not top_items:
        return Response({"error": f"No top-level assemblies found for complexity '{complexity}'."}, status=404)

    overall_results = []
    per_item_summary = []

    for item in top_items:
        simulations = simulate_quote_for_item(item, trials=50)
        if simulations:
            overall_results.extend(simulations)
            per_item_summary.append({
                "item_no": item.item_no,
                "description": item.description,
                "avg_time_sec": round(np.mean([r["total_time_sec"] for r in simulations]), 2),
                "avg_entries": round(np.mean([r["manual_entries"] for r in simulations]), 2),
                "avg_errors": round(np.mean([r["error_count"] for r in simulations]), 2),
            })

    overall_stats = {
        "complexity": complexity,
        "total_items_simulated": len(per_item_summary),
        "overall_avg_time_sec": round(np.mean([r["total_time_sec"] for r in overall_results]), 2),
        "overall_avg_entries": round(np.mean([r["manual_entries"] for r in overall_results]), 2),
        "overall_avg_errors": round(np.mean([r["error_count"] for r in overall_results]), 2),
    }

    return Response({
        "summary": overall_stats,
        "per_item": per_item_summary,
    })

@api_view(['GET'])
def simulate_all_top_level_costing_sw_case(request):
    """
    Simulate quoting process for all top-level assemblies in the system
    """
    # Step 1: Get all assemblies that are parents in BOMs
    parent_assemblies = BOM.objects.filter(
        parent__item_type='A'
    ).values_list('parent__item_no', flat=True)

    # Step 2: Exclude any assembly that appears as a component
    sub_assemblies = BOMLine.objects.filter(
        component__item_type='A'
    ).values_list('component__item_no', flat=True)

    top_level_item_nos = set(parent_assemblies) - set(sub_assemblies)
    # Safer filtering in Python to avoid hitting SQL variable limits
    all_assemblies = Item.objects.filter(item_type='A').select_related()
    top_items = [item for item in all_assemblies if item.item_no in top_level_item_nos]


    if not top_items:
        return Response({"error": "No top-level assemblies found."}, status=404)

    overall_results = []
    per_item_summary = []

    for item in top_items:
        simulations = simulate_quote_for_item_sw(item, trials=50)
        if simulations:
            overall_results.extend(simulations)
            per_item_summary.append({
                "item_no": item.item_no,
                "description": item.description,
                "avg_time_sec": round(np.mean([r["total_time_sec"] for r in simulations]), 2),
                "avg_entries": round(np.mean([r["manual_entries"] for r in simulations]), 2),
                "avg_errors": round(np.mean([r["error_count"] for r in simulations]), 2),
            })

    overall_stats = {
        "total_items_simulated": len(per_item_summary),
        "overall_avg_time_sec": round(np.mean([r["total_time_sec"] for r in overall_results]), 2),
        "overall_avg_entries": round(np.mean([r["manual_entries"] for r in overall_results]), 2),
        "overall_avg_errors": round(np.mean([r["error_count"] for r in overall_results]), 2),
    }

    #save results and summary to file
    unique_id = str(int(time.time()))
    with open(f"base_case_simulation_results_{unique_id}.json", "w") as f:
        json.dump({
            "overall_stats": overall_stats,
            "per_item_summary": per_item_summary,
            "overall_results": overall_results,
        }, f, indent=4)

    return Response({
        "summary": overall_stats,})