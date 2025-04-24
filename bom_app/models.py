from django.db import models

# bom_app/models.py

class Item(models.Model):
    ITEM_TYPES = [('P','Part'),('A','Assembly')]
    item_no      = models.CharField(max_length=10, unique=True)
    description  = models.CharField(max_length=100)
    item_type    = models.CharField(choices=ITEM_TYPES, max_length=1)
    base_cost    = models.FloatField()
    process_cost = models.FloatField(default=0.0)   # <-- new
    total_cost   = models.FloatField()

    def __str__(self):
        return self.item_no
    
    def calculate_total_cost(self):
        """Calculate the total cost of this item including base, process, and component costs"""
        cost = self.base_cost + self.process_cost
        
        # If this is an assembly, add component costs
        if self.item_type == 'A':
            # Get the BOM for this assembly
            try:
                bom = self.booms.first()  # Using the related_name from the ForeignKey
                if bom:
                    for line in bom.lines.all():
                        cost += line.component.total_cost * line.quantity
            except BOM.DoesNotExist:
                pass
                
        return cost
    
    def update_total_cost(self):
        """Update the total_cost field based on current calculations"""
        self.total_cost = self.calculate_total_cost()
        self.save(update_fields=['total_cost'])

class BOM(models.Model):
    bom_no   = models.CharField(max_length=15, unique=True)
    parent   = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='booms')
    depth     = models.IntegerField()
    complexity= models.CharField(max_length=10)

class BOMLine(models.Model):
    bom        = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name='lines')
    component  = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity   = models.IntegerField()

class WorkCenter(models.Model):
    wc_no         = models.CharField(max_length=5, unique=True)
    name          = models.CharField(max_length=50)
    cost_per_min  = models.FloatField()

class RoutingStep(models.Model):
    routing_no     = models.CharField(max_length=20)
    bom            = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name='routing')
    wc             = models.ForeignKey(WorkCenter, on_delete=models.CASCADE)
    step_no        = models.IntegerField()
    run_time_min   = models.IntegerField()