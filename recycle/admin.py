from django.contrib import admin
from recycle.models import ScrapCategory, ScrapRequest, ScrapOffer

# Register your models here.
admin.site.register(ScrapCategory)
admin.site.register(ScrapRequest)
admin.site.register(ScrapOffer)
