# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
import json, logging

from urllib import request
from django.conf import settings
from multitier.thread_locals import get_current_site

LOGGER = logging.getLogger(__name__)

class NotificationWebhookBackend(object):
    def send_notification(self, event_name, context=None, site=None, recipients=None):
        webhook_url = settings.NOTIFICATION_WEBHOOK_URL

        context.update({"event": event_name})

        if not site:
            site = get_current_site()

        body = json.dumps({
            'context': context,
            'site': site.slug,
            'recipients': recipients
        }).encode('utf8')

        req = request.Request(webhook_url, data=body, headers={
            'Content-Type': 'application/json'})
        try:
            request.urlopen(req)
        except Exception as err:
            LOGGER.exception(err)