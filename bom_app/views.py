# views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Item, BOM, BOMLine, WorkCenter, RoutingStep
from .serializers import BOMTreeSerializer
from django.shortcuts import render
import random

def build_tree(item_no, level=0, max_nodes=200):
    data = {
        'item_no': item_no,
        'description': Item.objects.get(item_no=item_no).description,
        'cost': float(Item.objects.get(item_no=item_no).total_cost),
        'level': level,
        'children': []
    }
    try:
        bom = BOM.objects.get(parent__item_no=item_no)
    except BOM.DoesNotExist:
        return data
    for line in bom.lines.all():
        if len(data['children'])<max_nodes:
            data['children'].append(
                build_tree(line.component.item_no, level+1, max_nodes)
            )
    return data

@api_view(['GET'])
def bom_tree(request, complexity):
    """
    Retrieves a random top-level BOM of the specified complexity
    """
    # Find all assemblies that are parents in BOMs of the specified complexity
    parent_assemblies = BOM.objects.filter(
        complexity=complexity, 
        parent__item_type='A'
    ).values_list('parent__item_no', flat=True)
    
    # Find assemblies that appear as components in other BOMs
    sub_assemblies = BOMLine.objects.filter(
        component__item_type='A'
    ).values_list('component__item_no', flat=True)
    
    # Get only top-level assemblies (those that aren't components in other BOMs)
    top_level_item_nos = set(parent_assemblies) - set(sub_assemblies)
    
    if not top_level_item_nos:
        return Response({"error": f"No top-level assemblies found with complexity '{complexity}'"}, status=404)
    
    # Pick a random top-level assembly
    chosen_item_no = random.choice(list(top_level_item_nos))
    bom = BOM.objects.get(parent__item_no=chosen_item_no)
    
    tree = build_tree(bom.parent.item_no)
    return Response(tree)

def tree_view(request):
    template = "bom_app/index.html"
    context = {
        'title': 'BOM Tree View',
        'description': 'This is a tree view of the BOM.',
    }
    return render(request, template, context)


def collect_routing_data(item_no, level=0, max_nodes=200):
    """
    Recursively collect routing data for a BOM and its components
    """
    item = Item.objects.get(item_no=item_no)
    
    # Initialize data structure
    data = {
        'item_no': item_no,
        'description': item.description,
        'item_type': item.item_type,
        'level': level,
        'work_centers': {},
        'total_time': 0,
        'children': []
    }
    
    try:
        bom = BOM.objects.get(parent__item_no=item_no)
        
        # Get all work centers
        work_centers = WorkCenter.objects.all()
        
        # Initialize work center times to 0
        for wc in work_centers:
            data['work_centers'][wc.wc_no] = 0
        
        # Get routing steps for this BOM
        routing_steps = RoutingStep.objects.filter(bom=bom)
        
        # Populate work center times
        for step in routing_steps:
            data['work_centers'][step.wc.wc_no] = step.run_time_min
            data['total_time'] += step.run_time_min
        
        # Recursively process children
        for line in bom.lines.all():
            if len(data['children']) < max_nodes:
                data['children'].append(
                    collect_routing_data(line.component.item_no, level+1, max_nodes)
                )
    except BOM.DoesNotExist:
        # For parts without BOMs, just return the basic data
        pass
    
    return data

@api_view(['GET'])
def bom_routing_table(request, complexity):
    """
    API endpoint to get routing data for a top-level BOM of the specified complexity
    """
    # Find all assemblies that are parents in BOMs of the specified complexity
    parent_assemblies = BOM.objects.filter(
        complexity=complexity, 
        parent__item_type='A'
    ).values_list('parent__item_no', flat=True)
    
    # Find assemblies that appear as components in other BOMs
    sub_assemblies = BOMLine.objects.filter(
        component__item_type='A'
    ).values_list('component__item_no', flat=True)
    
    # Get only top-level assemblies (those that aren't components in other BOMs)
    top_level_item_nos = set(parent_assemblies) - set(sub_assemblies)
    
    if not top_level_item_nos:
        return Response({"error": f"No top-level assemblies found with complexity '{complexity}'"}, status=404)
    
    # Pick a random top-level assembly
    chosen_item_no = random.choice(list(top_level_item_nos))
    bom = BOM.objects.get(parent__item_no=chosen_item_no)
    
    # Get all work centers for column headers
    work_centers = WorkCenter.objects.all().order_by('wc_no')
    
    # Get routing data
    routing_data = collect_routing_data(bom.parent.item_no)
    
    # Prepare response
    response = {
        'work_centers': [{'wc_no': wc.wc_no, 'name': wc.name} for wc in work_centers],
        'routing_data': routing_data
    }
    
    return Response(response)

def routing_table_view(request):
    """
    View function to render the routing table template
    """
    template = "bom_app/routing_table.html"
    
    # Get all work centers for the table header
    work_centers = WorkCenter.objects.all().order_by('wc_no')
    
    context = {
        'title': 'BOM Routing Table',
        'description': 'This shows work center operations for each component in the BOM.',
        'work_centers': work_centers,
    }
    return render(request, template, context)