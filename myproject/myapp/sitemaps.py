from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        # Replace 'landing' with your actual homepage URL name if different
        return ["landing"]

    def location(self, item):
        return reverse(item)
