from django.contrib import admin
from .models import Item, BOM, BOMLine, WorkCenter, RoutingStep

# Register your models here.
class ItemAdmin(admin.ModelAdmin):
    list_display = ('item_no', 'description', 'item_type', 'base_cost', 'total_cost')
    search_fields = ('item_no', 'description')
    list_filter = ('item_type',)
    ordering = ('item_no',)
    list_per_page = 20
    list_editable = ('base_cost', 'total_cost')
    actions = ['update_costs']

    def update_costs(self, request, queryset):
        for item in queryset:
            item.total_cost = item.base_cost * 1.2  # Example calculation
            item.save()
        self.message_user(request, "Costs updated successfully.")
    update_costs.short_description = "Update total costs for selected items"

class BOMAdmin(admin.ModelAdmin):
    list_display = ('bom_no', 'parent', 'depth', 'complexity')
    search_fields = ('bom_no', 'parent__item_no')
    list_filter = ('complexity',)
    ordering = ('bom_no',)
    list_per_page = 20
    actions = ['update_complexity']


    def update_complexity(self, request, queryset):
        for bom in queryset:
            if bom.complexity == 'simple':
                bom.complexity = 'complex'
            else:
                bom.complexity = 'simple'
            bom.save()
        self.message_user(request, "Complexity updated successfully.")

    update_complexity.short_description = "Toggle complexity for selected BOMs"

class BOMLineAdmin(admin.ModelAdmin):
    list_display = ('bom', 'component', 'quantity')
    search_fields = ('bom__bom_no', 'component__item_no')
    list_filter = ('bom__complexity',)
    ordering = ('bom',)
    list_per_page = 20
    actions = ['update_quantities']

    def update_quantities(self, request, queryset):
        for line in queryset:
            line.quantity += 1  # Example calculation
            line.save()
        self.message_user(request, "Quantities updated successfully.")
    update_quantities.short_description = "Increment quantities for selected BOM lines"


class WorkCenterAdmin(admin.ModelAdmin):
    list_display = ('wc_no', 'name', 'cost_per_min')
    search_fields = ('wc_no', 'name')
    list_filter = ('cost_per_min',)
    ordering = ('wc_no',)
    list_per_page = 20
    actions = ['update_costs']

    def update_costs(self, request, queryset):
        for wc in queryset:
            wc.cost_per_min *= 1.1  # Example calculation
            wc.save()
        self.message_user(request, "Costs updated successfully.")
    update_costs.short_description = "Update costs for selected work centers"
class RoutingStepAdmin(admin.ModelAdmin):
    list_display = ('routing_no', 'bom', 'wc', 'step_no', 'run_time_min')
    search_fields = ('routing_no', 'bom__bom_no', 'wc__wc_no')
    list_filter = ('bom__complexity',)
    ordering = ('routing_no',)
    list_per_page = 20
    actions = ['update_run_times']

    def update_run_times(self, request, queryset):
        for step in queryset:
            step.run_time_min += 5  # Example calculation
            step.save()
        self.message_user(request, "Run times updated successfully.")
    update_run_times.short_description = "Increment run times for selected routing steps"

admin.site.register(Item, ItemAdmin)
admin.site.register(BOM, BOMAdmin)
admin.site.register(BOMLine, BOMLineAdmin)
admin.site.register(WorkCenter, WorkCenterAdmin)
admin.site.register(RoutingStep, RoutingStepAdmin)
