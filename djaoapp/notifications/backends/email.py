# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import json, logging, smtplib

from deployutils.crypt import JSONEncoder
from django.conf import settings
from django.core.mail import get_connection as get_connection_base
from django.template import TemplateDoesNotExist
from django.utils import translation
from extended_templates.backends import get_email_backend
from multitier.thread_locals import get_current_site
from saas import settings as saas_settings
from saas.models import get_broker
from saas.utils import get_organization_model
from signup.models import Contact
from signup.settings import NOTIFICATIONS_OPT_OUT

from ...compat import six, import_string, gettext_lazy as _


LOGGER = logging.getLogger(__name__)


def _notified_managers(organization, notification_slug, originated_by=None):
    managers = organization.with_role(saas_settings.MANAGER)
    if originated_by:
        managers = managers.exclude(email=originated_by.get('email', ""))
    # checking whether those users are subscribed to the notification
    if NOTIFICATIONS_OPT_OUT:
        filtered = managers.exclude(notifications__slug=notification_slug)
    else:
        filtered = managers.filter(notifications__slug=notification_slug)
    return [notified.email for notified in filtered if notified.email]


def notified_recipients(notification_slug, context, broker=None, site=None):
    """
    Returns the organization email or the managers email if the organization
    does not have an e-mail set.
    """
    organization_model = get_organization_model()
    recipients = []
    bcc = []
    if not broker:
        broker = get_broker()
    if not site:
        site = get_current_site()
    originated_by = context.get('originated_by')
    if not originated_by:
        originated_by = {}
    reply_to = originated_by.get('email')
    if not reply_to and broker.email and broker.email != site.get_from_email():
        reply_to = broker.email

    # Notify a single user because there is a verification_key
    # in the e-mail body.
    if notification_slug in (
            'user_verification',
            'user_reset_password',
            'user_mfa_code',
            'user_welcome',
            'role_grant_created',):
        user = context.get('user')
        if user:
            user_email = user.get('email')
            if user_email:
                recipients = [user_email]

    # Notify the profile primary contact e-mail address
    elif notification_slug in (
            'claim_code_generated',
            'subscription_grant_created',
            'subscription_request_accepted',
            'role_request_created',
            'role_grant_accepted',
            'profile_updated',
            'order_executed',
            'card_updated',
            'charge_updated',
            'card_expires_soon',
            'expires_soon'):
        organization_email = context.get('profile', {}).get('email', "")
        if organization_email:
            recipients = [organization_email]
        if notification_slug in (
            'subscription_request_accepted',
            'role_request_created',
            'role_grant_accepted',
            'profile_updated',
            'order_executed',
            'card_updated',
            'charge_updated',
            'card_expires_soon',
            'expires_soon'):
            try:
                # When the theme editor attempts to "Send Test Email",
                # it is highly likely the sample data does not exist
                # in the database.
                organization = organization_model.objects.get(
                    slug=context.get('profile', {}).get('slug'))
                bcc = _notified_managers(organization, notification_slug,
                        originated_by=originated_by)
            except organization_model.DoesNotExist:
                bcc = []
            # We also notify the provider managers that are interested
            # in these events.
            if notification_slug in (
                'subscription_request_accepted',):
                try:
                    # When the theme editor attempts to "Send Test Email",
                    # it is highly likely the sample data does not exist
                    # in the database.
                    provider = organization_model.objects.get(
                        slug=context.get('provider', {}).get('slug'))
                    bcc += _notified_managers(provider, notification_slug,
                        originated_by=originated_by)
                except organization_model.DoesNotExist:
                    pass
            # We also notify the broker managers that are interested
            # in these events.
            elif notification_slug in (
                    'profile_updated',
                    'order_executed',
                    'card_updated',
                    'charge_updated',
                    'card_expires_soon',
                    'expires_soon'):
                bcc += _notified_managers(broker, notification_slug,
                    originated_by=originated_by)

    # Notify the provider primary contact e-mail address
    elif notification_slug in (
            'subscription_grant_accepted',
            'subscription_request_created'):
        provider_email = context.get(
            'plan', {}).get('organization', {}).get('email', "")
        if provider_email:
            recipients = [provider_email]
            try:
                # When the theme editor attempts to "Send Test Email",
                # it is highly likely the sample data does not exist
                # in the database.
                provider = organization_model.objects.get(
                    slug=context.get('profile', {}).get('slug'))
                bcc = _notified_managers(provider, notification_slug,
                    originated_by=originated_by)
            except organization_model.DoesNotExist:
                bcc = []
            try:
                # When the theme editor attempts to "Send Test Email",
                # it is highly likely the sample data does not exist
                # in the database.
                subscriber = organization_model.objects.get(
                    slug=context.get('subscriber', {}).get('slug'))
                bcc += _notified_managers(subscriber, notification_slug,
                    originated_by=originated_by)
            except organization_model.DoesNotExist:
                pass

    elif notification_slug in (
            'user_contact',
            'processor_setup_error',
            'user_registered',
            'user_activated',
            'weekly_sales_report_created'):
        # We are hanlding `recipients` a bit differently here because contact
        # requests are usually meant to be sent to a ticketing system.
        recipients = [broker.email]
        if notification_slug in (
                'processor_setup_error',
                'user_registered',
                'user_activated',
                'weekly_sales_report_created',):
            bcc = _notified_managers(broker, notification_slug)

    return recipients, bcc, reply_to


class NotificationEmailBackend(object):

    def send_notification(self, event_name, context=None, site=None,
                          recipients=None):
        """
        Sends a notification e-mail using the current site connection,
        defaulting to sending an e-mail to broker profile managers
        if there is any problem with the connection settings.
        """
        #pylint:disable=too-many-arguments
        if isinstance(settings.SEND_NOTIFICATION_CALLABLE, six.string_types):
            import_string(settings.SEND_NOTIFICATION_CALLABLE)(
                event_name, context=context, site=site, recipients=recipients)

        organization_model = get_organization_model()

        context.update({"event": event_name})
        template = 'notification/%s.eml' % event_name
        if event_name in ('role_grant_created',):
            role_description_slug = context.get(
                'role_description', {}).get('slug')
            if role_description_slug:
                template = [
                    "notification/%s_role_grant_created.eml" %
                    role_description_slug] + [template]
        if not site:
            site = get_current_site()

        bcc = []
        reply_to = recipients
        if not recipients:
            recipients, bcc, reply_to = notified_recipients(
                event_name, context)

        LOGGER.debug("djaoapp_extras.recipients.send_notification("\
            "recipients=%s, reply_to='%s', bcc=%s"\
            "event=%s)", recipients, reply_to, bcc,
            json.dumps(context, indent=2, cls=JSONEncoder))
        lang_code = None
        contact = Contact.objects.filter(
            email__in=recipients).order_by('email').first()
        if contact:
            lang_code = contact.lang

        if settings.SEND_EMAIL:
            try:
                with translation.override(lang_code):
                    get_email_backend(
                        connection=site.get_email_connection()).send(
                        from_email=site.get_from_email(),
                        recipients=recipients,
                        reply_to=reply_to,
                        bcc=bcc,
                        template=template,
                        context=context)
            except smtplib.SMTPException as err:
                LOGGER.warning("[signal] problem sending email from %s"\
                    " on connection for %s. %s",
                    site.get_from_email(), site, err)
                context.update({'errors': [_("There was an error sending"\
        " the following email to %(recipients)s. This is most likely due to"\
        " a misconfiguration of the e-mail notifications whitelabel settings"\
        " for your site %(site)s.") % {
            'recipients': recipients, 'site': site.as_absolute_uri()}]})
                #pylint:disable=unused-variable
                notified_on_errors, unused1, unused2 = notified_recipients(
                    '', {
                    #pylint:disable=protected-access
                    # We are emailing the owner of the site here so we want
                    # to access the information at the hosting provider.
                    'broker': organization_model.objects.using(
                        site._state.db).get(pk=site.account_id)})
                if notified_on_errors:
                    get_email_backend(
                        connection=get_connection_base(fail_silently=True)).send(
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipients=notified_on_errors,
                        template=template,
                        context=context)
            except TemplateDoesNotExist:
                # If there is a problem with the template, notify the user.
                raise
            except Exception as err:
                # Something went horribly wrong, like the email password was not
                # decrypted correctly. We want to notifiy the operations team
                # but the end user shouldn't see a 500 error as a result
                # of notifications sent in the HTTP request pipeline.
                LOGGER.exception(err)
