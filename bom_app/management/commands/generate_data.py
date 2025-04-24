# bom_app/management/commands/generate_data.py

import random, time
from django.core.management.base import BaseCommand
from django.db import transaction
from bom_app.models import (
    Item, BOM, BOMLine, WorkCenter, RoutingStep
)
import django.db.models as models

class Command(BaseCommand):
    help = "Generate synthetic parts, assemblies, BOMs, routings & costs"

    def handle(self, *args, **options):
        random.seed(time.time())

        # 1) Wipe out old data
        Item.objects.all().delete()
        BOM.objects.all().delete()
        BOMLine.objects.all().delete()
        WorkCenter.objects.all().delete()
        RoutingStep.objects.all().delete()

        # 2) Create WorkCenters
        wc_defs = [
            ("Cutting", 0.15),   
            ("Drilling", 0.20), 
            ("Welding", 0.30),   
            ("Painting", 0.25),  
            ("Assembly", 0.40),  
            ("QC", 0.10)         
        ]
        wcs = []
        for i,(name,cost) in enumerate(wc_defs, start=1):
            wc = WorkCenter.objects.create(
                wc_no=f"WC{i:02d}", name=name,
                cost_per_min=cost
            )
            wcs.append(wc)

        # 3) Create Parts and Assemblies
        part_categories = [
            {"name": "Fastener", "cost_range": (0.05, 0.5)},
            {"name": "Electronic", "cost_range": (1.0, 8.0)},
            {"name": "Structural", "cost_range": (0.8, 4.0)},
            {"name": "Mechanical", "cost_range": (1.2, 6.0)}
        ]

        parts = []
        for i in range(1, 501):
            category = random.choice(part_categories)
            p = Item.objects.create(
                item_no=f"P{i:04d}",
                description=f"{category['name']} {i:04d}",
                item_type='P',
                base_cost=random.uniform(*category['cost_range']),
                total_cost=0.0
            )
            parts.append(p)

        assemblies = []
        # Track the next available assembly number
        next_assembly_num = 1
        
        for i in range(1, 101):
            a = Item.objects.create(
                item_no=f"A{next_assembly_num:03d}",
                description=f"Assembly A{next_assembly_num:03d}",
                item_type='A',
                base_cost=random.uniform(2, 10),
                total_cost=0.0
            )
            assemblies.append(a)
            next_assembly_num += 1

        # Track which items already have BOMs to prevent duplicates
        items_with_boms = set()
        
        # Helper function to create a new unique assembly
        def create_new_assembly():
            nonlocal next_assembly_num
            new_item_no = f"A{next_assembly_num:03d}"
            new_sub = Item.objects.create(
                item_no=new_item_no,
                description=f"Assembly {new_item_no}",
                item_type='A',
                base_cost=random.uniform(2, 10),
                total_cost=0.0
            )
            assemblies.append(new_sub)
            next_assembly_num += 1
            return new_sub
        
        # 4) Pick finished products for each complexity
        available_assemblies = assemblies.copy()
        
        # 5) Generate BOMs with enforced complexity rules
        self.stdout.write("Generating BOMs with enforced complexity rules...")
        
        # Track which assemblies have been used
        used_assemblies = set()
        
        # Create simple BOMs (parts only, min 2 parts)
        simple_products = []
        for i in range(10):
            if not available_assemblies:
                break
                
            assembly = available_assemblies.pop(0)
            simple_products.append(assembly)
            used_assemblies.add(assembly.item_no)
            
            # Create BOM with only parts (2-20 parts)
            bom = BOM.objects.create(
                bom_no=f"BOM_S{i+1}_{assembly.item_no}",  # Ensure uniqueness
                parent=assembly,
                depth=0,
                complexity='simple'
            )
            items_with_boms.add(assembly.item_no)
            
            # Add minimum 2 parts, up to 20
            n_parts = random.randint(2, 20)
            comps = random.sample(parts, k=min(n_parts, len(parts)))
            
            for comp in comps:
                qty = random.randint(1, 10)
                BOMLine.objects.create(
                    bom=bom,
                    component=comp,
                    quantity=qty
                )
        
        # Create moderate BOMs (must include at least one sub-assembly)
        moderate_products = []
        for i in range(10):
            if not available_assemblies:
                break
                
            assembly = available_assemblies.pop(0)
            moderate_products.append(assembly)
            used_assemblies.add(assembly.item_no)
            
            # Create top-level BOM
            bom = BOM.objects.create(
                bom_no=f"BOM_M{i+1}_{assembly.item_no}",  # Ensure uniqueness
                parent=assembly,
                depth=0,
                complexity='moderate'
            )
            items_with_boms.add(assembly.item_no)
            
            # Add parts (3-15 parts)
            n_parts = random.randint(3, 15)
            part_comps = random.sample(parts, k=min(n_parts, len(parts)))
            
            for comp in part_comps:
                qty = random.randint(1, 10)
                BOMLine.objects.create(
                    bom=bom,
                    component=comp,
                    quantity=qty
                )
            
            # Add 1-3 sub-assemblies (must have at least 1)
            n_subs = random.randint(1, 3)
            available_subs = [a for a in available_assemblies if a.item_no not in used_assemblies]
            
            if len(available_subs) < n_subs:
                n_subs = len(available_subs)
                
            if n_subs == 0:
                # If we run out of assemblies, create a new one
                new_sub = create_new_assembly()
                available_subs = [new_sub]
                n_subs = 1
            
            sub_comps = random.sample(available_subs, k=n_subs)
            
            for j, comp in enumerate(sub_comps):
                used_assemblies.add(comp.item_no)
                if comp in available_assemblies:
                    available_assemblies.remove(comp)
                
                qty = random.randint(1, 5)
                BOMLine.objects.create(
                    bom=bom,
                    component=comp,
                    quantity=qty
                )
                
                # Create sub-assembly BOM (parts only) if it doesn't already have one
                if comp.item_no not in items_with_boms:
                    sub_bom = BOM.objects.create(
                        bom_no=f"BOM_M{i+1}_SUB{j+1}_{comp.item_no}",  # Ensure uniqueness
                        parent=comp,
                        depth=1,
                        complexity='moderate'
                    )
                    items_with_boms.add(comp.item_no)
                    
                    # Add minimum 2 parts, up to 15
                    n_sub_parts = random.randint(2, 15)
                    sub_part_comps = random.sample(parts, k=min(n_sub_parts, len(parts)))
                    
                    for sub_comp in sub_part_comps:
                        sub_qty = random.randint(1, 10)
                        BOMLine.objects.create(
                            bom=sub_bom,
                            component=sub_comp,
                            quantity=sub_qty
                        )
        
        # Create complex BOMs (must have sub-assemblies with their own sub-assemblies)
        complex_products = []
        for i in range(10):
            if not available_assemblies:
                break
                
            assembly = available_assemblies.pop(0)
            complex_products.append(assembly)
            used_assemblies.add(assembly.item_no)
            
            # Create top-level BOM
            bom = BOM.objects.create(
                bom_no=f"BOM_C{i+1}_{assembly.item_no}",  # Ensure uniqueness
                parent=assembly,
                depth=0,
                complexity='complex'
            )
            items_with_boms.add(assembly.item_no)
            
            # Add parts (2-10 parts)
            n_parts = random.randint(2, 10)
            part_comps = random.sample(parts, k=min(n_parts, len(parts)))
            
            for comp in part_comps:
                qty = random.randint(1, 10)
                BOMLine.objects.create(
                    bom=bom,
                    component=comp,
                    quantity=qty
                )
            
            # Add 2-5 level-1 sub-assemblies (must have at least 2)
            n_subs = random.randint(2, 5)
            available_subs = [a for a in available_assemblies if a.item_no not in used_assemblies]
            
            if len(available_subs) < n_subs:
                # Create more assemblies if needed
                needed = n_subs - len(available_subs)
                new_subs = []
                for _ in range(needed):
                    new_subs.append(create_new_assembly())
                available_subs.extend(new_subs)
            
            level1_subs = random.sample(available_subs, k=n_subs)
            
            # We need at least one level-1 sub to have its own sub-assembly
            has_level2 = False
            
            for j, comp in enumerate(level1_subs):
                used_assemblies.add(comp.item_no)
                if comp in available_assemblies:
                    available_assemblies.remove(comp)
                
                qty = random.randint(1, 5)
                BOMLine.objects.create(
                    bom=bom,
                    component=comp,
                    quantity=qty
                )
                
                # Create level-1 sub-assembly BOM if it doesn't already have one
                if comp.item_no not in items_with_boms:
                    sub_bom = BOM.objects.create(
                        bom_no=f"BOM_C{i+1}_L1_{j+1}_{comp.item_no}",  # Ensure uniqueness
                        parent=comp,
                        depth=1,
                        complexity='complex'
                    )
                    items_with_boms.add(comp.item_no)
                    
                    # Add parts to level-1 sub-assembly (2-10 parts)
                    n_sub_parts = random.randint(2, 10)
                    sub_part_comps = random.sample(parts, k=min(n_sub_parts, len(parts)))
                    
                    for sub_comp in sub_part_comps:
                        sub_qty = random.randint(1, 10)
                        BOMLine.objects.create(
                            bom=sub_bom,
                            component=sub_comp,
                            quantity=sub_qty
                        )
                    
                    # Decide if this level-1 sub should have its own sub-assembly
                    # Force at least one to have a level-2 sub
                    should_have_level2 = not has_level2 or random.random() < 0.7
                    
                    if should_have_level2:
                        has_level2 = True
                        available_level2_subs = [a for a in available_assemblies if a.item_no not in used_assemblies]
                        
                        if not available_level2_subs:
                            # Create a new assembly if needed
                            level2_sub = create_new_assembly()
                        else:
                            level2_sub = random.choice(available_level2_subs)
                            
                        used_assemblies.add(level2_sub.item_no)
                        if level2_sub in available_assemblies:
                            available_assemblies.remove(level2_sub)
                        
                        # Add level-2 sub to level-1 sub
                        BOMLine.objects.create(
                            bom=sub_bom,
                            component=level2_sub,
                            quantity=random.randint(1, 3)
                        )
                        
                        # Create level-2 sub-assembly BOM if it doesn't already have one
                        if level2_sub.item_no not in items_with_boms:
                            level2_bom = BOM.objects.create(
                                bom_no=f"BOM_C{i+1}_L2_{j+1}_{level2_sub.item_no}",  # Ensure uniqueness
                                parent=level2_sub,
                                depth=2,
                                complexity='complex'
                            )
                            items_with_boms.add(level2_sub.item_no)
                            
                            # Add minimum 2 parts to level-2 sub
                            n_level2_parts = random.randint(2, 8)
                            level2_part_comps = random.sample(parts, k=min(n_level2_parts, len(parts)))
                            
                            for level2_comp in level2_part_comps:
                                level2_qty = random.randint(1, 5)
                                BOMLine.objects.create(
                                    bom=level2_bom,
                                    component=level2_comp,
                                    quantity=level2_qty
                                )

        # 6.5) Create "manufacturing BOMs" for parts that need routing
        self.stdout.write("Creating manufacturing BOMs for parts...")
        # Take a sample of parts that will have manufacturing processes
        manufacturing_parts = random.sample(parts, k=int(len(parts) * 0.8))  # 80% of parts have manufacturing
        
        for i, part in enumerate(manufacturing_parts):
            # Create a manufacturing BOM for the part with a unique bom_no
            bom = BOM.objects.create(
                bom_no=f"MFG_P{i+1}_{part.item_no}",  # Ensure uniqueness
                parent=part,
                depth=0,  # Manufacturing BOMs are always at depth 0
                complexity="part"  # Mark as a part BOM
            )

        # 7) Generate Routings + compute process_cost on each item
        assembly_wc = next((wc for wc in wcs if wc.name == "Assembly"), None)
        welding_wc = next((wc for wc in wcs if wc.name == "Welding"), None)
        qc_wc = next((wc for wc in wcs if wc.name == "QC"), None)

        for bom in BOM.objects.select_related('parent'):
            total_proc = 0.0
            steps_created = []
            
            # Determine number of steps based on item type
            if bom.parent.item_type == 'P':
                # Parts typically have 1-3 manufacturing steps
                num_steps = random.randint(1, 3)
                # Parts should only use certain work centers (not Assembly)
                available_wcs = [wc for wc in wcs if wc.name != "Assembly"]
                
                # Generate random manufacturing steps
                for idx in range(num_steps):
                    wc = random.choice(available_wcs)
                    time_min = random.randint(3, 15)
                    step = RoutingStep.objects.create(
                        routing_no=f"RT_{bom.bom_no}",
                        bom=bom,
                        wc=wc,
                        step_no=idx+1,
                        run_time_min=time_min
                    )
                    steps_created.append(step)
                    total_proc += wc.cost_per_min * time_min
                    
            else:  # Assembly
                # Check if this assembly has components (in-house manufactured)
                has_components = bom.lines.exists()
                
                if has_components:
                    # For assemblies, we need either Assembly or Welding (or both)
                    uses_assembly = random.random() < 0.8  # 80% use Assembly
                    uses_welding = random.random() < 0.4   # 40% use Welding
                    
                    # If neither was selected, force one of them
                    if not uses_assembly and not uses_welding:
                        if random.random() < 0.5:
                            uses_assembly = True
                        else:
                            uses_welding = True
                    
                    # Add other manufacturing operations (0-2 steps)
                    other_ops = random.randint(0, 2)
                    other_wcs = [wc for wc in wcs if wc.name not in ["Assembly", "Welding", "QC"]]
                    
                    for idx in range(other_ops):
                        wc = random.choice(other_wcs)
                        time_min = random.randint(5, 15)
                        step = RoutingStep.objects.create(
                            routing_no=f"RT_{bom.bom_no}",
                            bom=bom,
                            wc=wc,
                            step_no=len(steps_created) + 1,
                            run_time_min=time_min
                        )
                        steps_created.append(step)
                        total_proc += wc.cost_per_min * time_min
                    
                    # Add Welding if needed
                    if uses_welding and welding_wc:
                        component_count = bom.lines.count()
                        welding_time = 5 + min(30, component_count * 1.5)  # Base 5 min + 1.5 min per component
                        
                        step = RoutingStep.objects.create(
                            routing_no=f"RT_{bom.bom_no}",
                            bom=bom,
                            wc=welding_wc,
                            step_no=len(steps_created) + 1,
                            run_time_min=welding_time
                        )
                        steps_created.append(step)
                        total_proc += welding_wc.cost_per_min * welding_time
                    
                    # Add Assembly if needed
                    if uses_assembly and assembly_wc:
                        component_count = bom.lines.count()
                        assembly_time = 5 + min(40, component_count * 2)  # Base 5 min + 2 min per component
                        
                        step = RoutingStep.objects.create(
                            routing_no=f"RT_{bom.bom_no}",
                            bom=bom,
                            wc=assembly_wc,
                            step_no=len(steps_created) + 1,
                            run_time_min=assembly_time
                        )
                        steps_created.append(step)
                        total_proc += assembly_wc.cost_per_min * assembly_time
                    
                    # Add QC as final step for most assemblies
                    if qc_wc and random.random() < 0.7:
                        qc_time = 5 + min(15, component_count)  # Base 5 min + 1 min per component
                        step = RoutingStep.objects.create(
                            routing_no=f"RT_{bom.bom_no}",
                            bom=bom,
                            wc=qc_wc,
                            step_no=len(steps_created) + 1,
                            run_time_min=qc_time
                        )
                        steps_created.append(step)
                        total_proc += qc_wc.cost_per_min * qc_time
                else:
                    # Purchased assembly - just add QC
                    if qc_wc:
                        time_min = random.randint(3, 10)
                        step = RoutingStep.objects.create(
                            routing_no=f"RT_{bom.bom_no}",
                            bom=bom,
                            wc=qc_wc,
                            step_no=1,
                            run_time_min=time_min
                        )
                        steps_created.append(step)
                        total_proc += qc_wc.cost_per_min * time_min

            # Store the routing/process cost on the parent item
            item = bom.parent
            item.process_cost = getattr(item, 'process_cost', 0.0) + total_proc
            item.save(update_fields=['process_cost'])

        # 8) Bottom‑up total cost roll‑up
        with transaction.atomic():
            # First, set total_cost = base_cost + process_cost for all parts
            Item.objects.filter(item_type='P').update(
                total_cost=models.F('base_cost') + models.F('process_cost')
            )
            
            # Then do the assembly roll-up by depth
            max_bom_depth = BOM.objects.aggregate(m=models.Max('depth'))['m'] or 0
            for d in range(max_bom_depth, -1, -1):
                boms_at_d = BOM.objects.filter(depth=d).select_related('parent').prefetch_related('lines__component')
                for bom in boms_at_d:
                    parent = bom.parent
                    # Skip if this is a manufacturing BOM for a part (already handled above)
                    if bom.complexity == "part":
                        continue
                        
                    comp_cost = 0.0
                    for line in bom.lines.all():
                        comp = line.component
                        comp_cost += comp.total_cost * line.quantity
                    # total_cost = base_cost + process_cost + component costs
                    parent.total_cost = parent.base_cost + parent.process_cost + comp_cost
                    parent.save(update_fields=['total_cost'])

        self.stdout.write(self.style.SUCCESS("Data generation complete."))