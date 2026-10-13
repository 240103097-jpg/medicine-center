from django.contrib import admin
from django.utils import timezone
from .models import Slot


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ["doctor", "local_start", "local_end"]
    readonly_fields = ["local_end"]
    fields = ["doctor", "start", "local_end"]

    @admin.display(description="Start (Asia/Almaty)", ordering="start")
    def local_start(self, obj):
        return timezone.localtime(obj.start).strftime("%Y-%m-%d %H:%M")

    @admin.display(description="End (Asia/Almaty)")
    def local_end(self, obj):
        return timezone.localtime(obj.end).strftime("%Y-%m-%d %H:%M") if obj.start else "—"
