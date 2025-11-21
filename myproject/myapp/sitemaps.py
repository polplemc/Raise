from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        # Use the actual name of your homepage URL pattern
        return ["landing"]

    def location(self, item):
        return reverse(item)
