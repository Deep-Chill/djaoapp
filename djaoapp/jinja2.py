# Copyright (c) 2022, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from django.conf import settings
import django.template.defaulttags
from django.utils.translation import gettext, ngettext
from deployutils.apps.django.themes import get_template_search_path
from deployutils.apps.django.templatetags import deployutils_extratags
from extended_templates import signals as extended_templates_signals
from jinja2.ext import i18n
from jinja2.sandbox import SandboxedEnvironment as Jinja2Environment
import multitier.templatetags.multitier_tags
import saas.templatetags.saas_tags

from .compat import import_string, reverse, six
import djaoapp.templatetags.djaoapp_tags


class DjaoappEnvironment(Jinja2Environment):

    def get_template(self, name, parent=None, globals=None):
        #pylint:disable=redefined-builtin
        template = super(DjaoappEnvironment, self).get_template(
            name, parent=parent, globals=globals)
        extended_templates_signals.template_loaded.send(
            sender=self, template=template)
        return template


def environment(**options):
    #pylint:disable=too-many-statements
    from django.contrib.auth import get_user_model
    from signup.models import ActivatedUserManager

    # Hack to install our create_user method.
    user_class = get_user_model()
    user_class.objects = ActivatedUserManager()
    user_class.objects.model = user_class

    # If we don't force ``auto_reload`` to True, in DEBUG=0, the templates
    # would only be compiled on the first edit.
    options.update({'auto_reload': True, 'bytecode_cache': None})
    if 'loader' in options:
        if isinstance(options['loader'], six.string_types):
            loader_class = import_string(options['loader'])
        else:
            loader_class = options['loader'].__class__
        options['loader'] = loader_class(get_template_search_path())
    env = DjaoappEnvironment(extensions=[i18n], **options)
    # i18n
    env.install_gettext_callables(gettext=gettext, ngettext=ngettext,
        newstyle=True)
    # Generic filters to render templates
    env.filters['asset'] = multitier.templatetags.multitier_tags.asset
    env.filters['site_url'] = multitier.templatetags.multitier_tags.site_url
    env.filters['site_printable_name'] = \
        multitier.templatetags.multitier_tags.site_printable_name

    env.filters['djasset'] = djaoapp.templatetags.djaoapp_tags.djasset
    env.filters['host'] = deployutils_extratags.host
    env.filters['is_authenticated'] = \
        djaoapp.templatetags.djaoapp_tags.is_authenticated
    env.filters['is_checkbox'] = djaoapp.templatetags.djaoapp_tags.is_checkbox
    env.filters['is_radio'] = djaoapp.templatetags.djaoapp_tags.is_radio
    env.filters['is_textarea'] = djaoapp.templatetags.djaoapp_tags.is_textarea
    env.filters['iterfields'] = djaoapp.templatetags.djaoapp_tags.iterfields
    env.filters['iteritems'] = saas.templatetags.saas_tags.iteritems
    env.filters['messages'] = djaoapp.templatetags.djaoapp_tags.messages
    env.filters['no_cache'] = djaoapp.templatetags.djaoapp_tags.no_cache
    env.filters['pluralize'] = djaoapp.templatetags.djaoapp_tags.pluralize
    env.filters['to_json'] = deployutils_extratags.to_json

    # Standard site pages
    env.filters['url_app'] = djaoapp.templatetags.djaoapp_tags.url_app
    env.filters['url_contact'] = djaoapp.templatetags.djaoapp_tags.url_contact
    env.filters['url_home'] = djaoapp.templatetags.djaoapp_tags.url_home
    env.filters['url_login'] = djaoapp.templatetags.djaoapp_tags.url_login
    env.filters['url_logout'] = djaoapp.templatetags.djaoapp_tags.url_logout
    env.filters['url_pricing'] = djaoapp.templatetags.djaoapp_tags.url_pricing
    env.filters['url_profile'] = djaoapp.templatetags.djaoapp_tags.url_profile
    env.filters['url_register'] \
        = djaoapp.templatetags.djaoapp_tags.url_register
    # Specific to SaaS
    env.filters['price'] = saas.templatetags.saas_tags.price
    env.filters['dest_price'] = saas.templatetags.saas_tags.dest_price
    env.filters['orig_price'] = saas.templatetags.saas_tags.orig_price
    env.filters['isoformat'] = saas.templatetags.saas_tags.isoformat
    env.filters['short_date'] = saas.templatetags.saas_tags.short_date
    env.filters['humanize_percent'] \
        = saas.templatetags.saas_tags.humanize_percent
    env.filters['humanize_period'] = saas.templatetags.saas_tags.humanize_period
    env.filters['humanize_money'] = saas.templatetags.saas_tags.humanize_money
    env.filters['date_in_future'] = saas.templatetags.saas_tags.date_in_future
    env.filters['md'] = saas.templatetags.saas_tags.md
    env.filters['describe'] = saas.templatetags.saas_tags.describe
    env.filters['describe_no_links'] = \
        saas.templatetags.saas_tags.describe_no_links

    env.globals.update({
        'DATETIME_FORMAT': "MMM dd, yyyy",
    })
    if settings.DEBUG:
        env.filters['addslashes'] = django.template.defaultfilters.addslashes
        env.globals.update({
            'ASSETS_DEBUG': settings.ASSETS_DEBUG,
            'FEATURES_DEBUG': settings.FEATURES_DEBUG,
            'url': reverse,
            'cycle': django.template.defaulttags.cycle,
        })
    if settings.API_DEBUG:
        env.filters['query_parameters'] = \
            djaoapp.templatetags.djaoapp_tags.query_parameters
        env.filters['request_body_parameters'] = \
            djaoapp.templatetags.djaoapp_tags.request_body_parameters
        env.filters['responses_parameters'] = \
            djaoapp.templatetags.djaoapp_tags.responses_parameters
        env.filters['schema_properties'] = \
            djaoapp.templatetags.djaoapp_tags.schema_properties
        env.filters['not_key'] = \
            djaoapp.templatetags.djaoapp_tags.not_key

    return env
