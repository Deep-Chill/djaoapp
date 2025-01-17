# Copyright (c) 2023 DjaoDjin inc.
# see LICENSE

from rest_framework import serializers
from saas.api.serializers import (PlanSerializer, ChargeSerializer,
    ChargeItemSerializer, CartItemSerializer, PriceSerializer,
    RoleDescriptionSerializer, TransactionSerializer)
from saas.utils import get_user_serializer
from signup.serializers_overrides import UserDetailSerializer

from ..api.serializers import NoModelSerializer, ProfileSerializer
from ..compat import gettext_lazy as _


class NotificationSerializer(NoModelSerializer):

    broker = ProfileSerializer(
        help_text=_("Site on which the product is hosted"))
    back_url = serializers.URLField(
        help_text=_("Link back to the site"))

    class Meta:
        fields = ('broker', 'back_url')
        read_only_fields = ('broker', 'back_url')


class ContactUsValueTuple(serializers.ListField):

    child = serializers.CharField() # (key, value)
    min_length = 2
    max_length = 2


class ContactUsNotificationSerializer(NotificationSerializer):
    """
    Notification sent when a contact us form is processed
    """
    originated_by = UserDetailSerializer(
        help_text=_("the user at the origin of the notification"))
    provider = ProfileSerializer(required=False,
        help_text=_("provider when different from broker"))
    detail = serializers.ListField(child=ContactUsValueTuple(),
        help_text=_("information passed in the 'Contact us' form,"\
            " including message"))

    class Meta(NotificationSerializer.Meta):
        fields = NotificationSerializer.Meta.fields + (
            'originated_by', 'detail', 'provider',)
        read_only_fields = NotificationSerializer.Meta.fields + (
            'originated_by', 'detail', 'provider',)


class UserNotificationSerializer(NotificationSerializer):

    user = UserDetailSerializer(
        help_text=_("user the notification applies to"))

    class Meta(NotificationSerializer.Meta):
        fields = NotificationSerializer.Meta.fields + ('user',)
        read_only_fields = NotificationSerializer.Meta.fields + ('user',)


class ExpireUserNotificationSerializer(UserNotificationSerializer):
    """
    Base class that defines a user and an expiration date
    """
    nb_expiration_days = serializers.IntegerField(
        help_text=_("number of days the link is valid"))

    class Meta(NotificationSerializer.Meta):
        fields = UserNotificationSerializer.Meta.fields + (
            'nb_expiration_days',)
        read_only_fields = UserNotificationSerializer.Meta.fields + (
            'nb_expiration_days',)


class OneTimeCodeNotificationSerializer(ExpireUserNotificationSerializer):

    code = serializers.IntegerField(
        help_text=_("one-time code"))


class ProfileNotificationSerializer(NotificationSerializer):

    profile = ProfileSerializer(
        help_text=_("profile the notification relates to"))


class ExpireProfileNotificationSerializer(ProfileNotificationSerializer):
    """
    Base class that defines a profile and an expiration date
    """
    nb_expiration_days = serializers.IntegerField(
        help_text=_("number of days before the card expires"))
    last4 = serializers.CharField(
        help_text=_("Last 4 digits of the credit card on file"))
    exp_date = serializers.CharField(
        help_text=_("Expiration date of the credit card on file"))


class SubscriptionExpireNotificationSerializer(ProfileNotificationSerializer):
    """
    Notification sent when a subscription is about to expire
    """
    nb_expiration_days = serializers.IntegerField(
        help_text=_("number of days before the subscription expires"))
    plan = PlanSerializer(
        help_text=_("plan the subscription relates to"))
    provider = ProfileSerializer(required=False,
        help_text=_("provider when different from broker"))


class UpdateProfileNotificationSerializer(ProfileNotificationSerializer):
    """
    Base class that defines an update event for a profile
    """
    originated_by = UserDetailSerializer(
        help_text=_("the user at the origin of the notification"))


class ChangeProfileNotificationSerializer(UpdateProfileNotificationSerializer):

    changes = serializers.DictField( # XXX
        help_text=_("changes to the profile"))

class PeriodValuesSerializer(NoModelSerializer):

    last = serializers.CharField()
    prev = serializers.CharField()
    prev_year = serializers.CharField()

    class Meta:
        fields = ('last', 'prev', 'prev_year')
        read_only_fields = ('last', 'prev', 'prev_year')


class PeriodSalesReportRowSerializer(NoModelSerializer):

    key = serializers.CharField()
    vals = PeriodValuesSerializer()

    class Meta:
        fields = ('key', 'vals')
        read_only_fields = ('key', 'vals')


class AggregatedSalesNotificationSerializer(ProfileNotificationSerializer):

    table = PeriodSalesReportRowSerializer(many=True)
    date = serializers.DateTimeField(
        help_text=_("Date/time of creation (in ISO format)"))

    class Meta(ProfileNotificationSerializer.Meta):
        fields = ProfileNotificationSerializer.Meta.fields + ('table', 'date')
        read_only_fields = ProfileNotificationSerializer.Meta.read_only_fields\
            + ('table', 'date')


class OrderNotificationSerializer(UpdateProfileNotificationSerializer):

    provider = ProfileSerializer(required=False,
        help_text=_("provider when different from broker"))



class ChargeNotificationSerializer(OrderNotificationSerializer):

    charge_items = ChargeItemSerializer(many=True,
        help_text=_("the line items on the charge receipt"))
    charge_total = PriceSerializer(required=False,
        help_text=_("Total amount for the charge after refunds have"\
            " been applied"))

    created_by = get_user_serializer()
    charge = ChargeSerializer(
        help_text=_("the charge that relates to the notification"))


class RenewalFailedNotificationSerializer(ProfileNotificationSerializer):

    provider = ProfileSerializer(required=False,
        help_text=_("provider when different from broker"))
    invoiced_items = TransactionSerializer(many=True,
        help_text=_("Line items to charge for renewal"))
    charge_total = PriceSerializer(
        help_text=_("Total amount for the charge"))
    nb_renewal_attempts = serializers.IntegerField(
        help_text=_("number renewal attempts"))
    max_renewal_attempts = serializers.IntegerField(
        help_text=_("maximimum number of renewal attempts"))
    final_notice = serializers.BooleanField(
        help_text=_("true if this is the final notice before subscription"\
        " is canceled"))


class InvoiceNotificationSerializer(OrderNotificationSerializer):

    invoiced_items = TransactionSerializer(many=True,
        help_text=_("Line items to charge on checkout"))


class ClaimNotificationSerializer(OrderNotificationSerializer):

    cart_items = CartItemSerializer(many=True,
        help_text=_("Line items paid for already"))
    detail = serializers.CharField()


class ProcessorSetupNotificationSerializer(OrderNotificationSerializer):
    """
    Notification sent when a payment is processed but a processor was not set
    """
    detail = serializers.CharField()


class RoleRequestNotificationSerializer(UpdateProfileNotificationSerializer):

    user = UserDetailSerializer(
        help_text=_("user the notification applies to"))
    detail = serializers.CharField(
        help_text=_("optional message at the attention of the user"))


class RoleGrantNotificationSerializer(RoleRequestNotificationSerializer):

    role_description = RoleDescriptionSerializer(
        help_text=_("description of the role the notification is about"))


class SubscriptionAcceptedNotificationSerializer(
        OrderNotificationSerializer):
    """
    Notification sent when a subscription grant, or request, was accepted
    """
    plan = PlanSerializer(
        help_text=_("plan the subscription relates to"))


class SubscriptionCreatedNotificationSerializer(
        SubscriptionAcceptedNotificationSerializer):
    """
    Notification sent when a subscription was granted or requested
    """
    detail = serializers.CharField(
        help_text=_("optional message at the attention of the profile"))
