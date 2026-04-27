from django.urls import reverse
from django.utils.html import format_html

class NavigationButtonMixin:
    def nav_button(self, label, url_name, obj_id=None, params=None):
        if obj_id:
            url = reverse(url_name, args=[obj_id])
        else:
            url = reverse(url_name)

        if params:
            query = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query}"

        return format_html(
            '<a style="padding:2px 6px; background:#1e88e5; color:white; '
            'border-radius:3px; font-size:11px; text-decoration:none;" href="{}">{}</a>',
            url, label
        )

