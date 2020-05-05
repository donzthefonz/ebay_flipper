from django.db import models
import datetime
import pytz
import logging
import os
from django.conf import settings
from datetime import timezone
import html2text

from djmoney.models.fields import MoneyField
from ebaysdk.finding import Connection as Finding
from ebaysdk.shopping import Connection as Shopping
import discord

# Import smtplib for the actual sending function
import smtplib
# Import the email modules we'll need
from email.mime.text import MIMEText

# from django.contrib.postgres.fields import ArrayField

db_logger = logging.getLogger('db')

localtimezone = pytz.timezone('Europe/London')


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=localtimezone)


class KeyWordString(models.Model):
    """ Currently not used, could be used later to improve anti keywords administration."""
    text = models.CharField(max_length=200)


class NotificationRoute(models.Model):
    """ Routes for notifications. """

    EDITABLE_FIELDS = ['name', 'description', 'webhook', 'created_by', 'insert_date', 'modified_date']
    DISPLAY_FIELDS = ['name', 'description', 'webhook', 'created_by', 'insert_date', 'modified_date']

    TYPE_CHOICES = [
        ('DIS', 'Discord'),
        ('SLK', 'Slack'),
        ('EMA', 'Email')
    ]

    name = models.CharField(max_length=400)
    description = models.CharField(max_length=400)
    webhook = models.CharField(max_length=400)
    type = models.CharField(max_length=3, choices=TYPE_CHOICES, null=False)
    include_item_description = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                   related_name='notifications')
    insert_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    # MANAGERS
    objects = models.Manager()

    # META CLASS
    class Meta:
        verbose_name = 'Notification Route'
        verbose_name_plural = 'Notification Routes'

    # TO STRING METHOD
    def __str__(self):
        return '{}'.format(self.name)

    # SAVE METHOD
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Call the "real" save() method.

    # OTHER METHODS
    pass


# Create your models here.
class WantedItem(models.Model):
    """ Specification for an item to monitor and send alerts for. """

    EDITABLE_FIELDS = ['name', 'keywords', 'anti_keywords', 'min_price', 'max_price', 'min_feedback', 'max_feedback',
                       'auction_alert_time', 'buy_it_now_time', 'condition', 'notifications']
    DISPLAY_FIELDS = ['name', 'keywords', 'anti_keywords', 'min_price', 'max_price', 'min_feedback', 'max_feedback',
                      'auction_alert_time', 'buy_it_now_time', 'condition']
    CONDITION_CHOICES = [
        (0000, 'N/A'),
        (1000, 'New'),
        (1500, 'New Other'),
        (1750, 'New with defects'),
        (2000, 'Manufacturer refurbished'),
        (2500, 'Seller refurbished'),
        (2750, 'Like New'),
        (3000, 'Used'),
        (4000, 'Very Good'),
        (5000, 'Good'),
        (6000, 'Acceptable'),
        (7000, 'For parts or not working'),
    ]

    name = models.CharField(max_length=200, default='Wanted Item...')
    keywords = models.CharField(max_length=500)
    # anti_keywords = ArrayField(models.CharField(max_length=100, blank=True))
    # anti_keywords = models.ManyToManyField(KeyWordString, blank=True, null=True)
    anti_keywords = models.TextField(blank=True)
    min_price = MoneyField(
        decimal_places=2,
        default=0,
        default_currency='GBP',
        max_digits=11,
    )
    max_price = MoneyField(
        decimal_places=2,
        default=0,
        default_currency='GBP',
        max_digits=11,
    )
    min_feedback = models.IntegerField(default=5)
    max_feedback = models.IntegerField(default=1000)
    auction_alert_time = models.IntegerField(default=15)  # alerts get sent this many minutes before end of auction
    buy_it_now_time = models.IntegerField(
        default=10)  # ignore buy it now items that have been listed for longer duration than this in minutes
    condition = models.IntegerField(choices=CONDITION_CHOICES, null=True, default=None)
    located_in = models.CharField(max_length=30, default='GB')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                   related_name='wanted_items')
    notifications = models.ManyToManyField(NotificationRoute, related_name='wanted_items')
    deleted = models.BooleanField(default=False)
    api = None
    found_items = []  # List of EbayItem

    # MANAGERS
    objects = models.Manager()

    # META CLASS
    class Meta:
        verbose_name = 'Wanted Item'
        verbose_name_plural = 'Wanted Items'

    # TO STRING METHOD
    def __str__(self):
        return '{}'.format(self.name)

    # SAVE METHOD
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Call the "real" save() method.

    # OTHER METHODS
    def connect(self, connection_type="Finding"):
        if connection_type == "Finding":
            self.api = Finding(appid=os.getenv("EBAY_API_ID"), siteid='EBAY-GB', config_file=None)
        elif connection_type == "Shopping":
            self.api = Shopping(appid=os.getenv("EBAY_API_ID"), siteid='EBAY-GB', config_file=None)

    def search_buy_it_now(self):
        try:
            api_request = {
                'keywords': self.keywords,
                'itemFilter': [
                    {'name': 'FeedbackScoreMin',
                     'value': self.min_feedback},
                    {'name': 'MaxPrice',
                     'value': self.max_price.amount},
                    {'name': 'MinPrice',
                     'value': self.min_price.amount},
                    {'name': 'LocatedIn',
                     'value': self.located_in},
                    {'name': 'ListingType',
                     'value': 'FixedPrice'},
                ],
                'sortOrder': 'StartTimeNewest',
                'descriptionSearch': True,
                'outputSelector': 'SellerInfo',
            }

            if self.condition is not 0:
                api_request['itemFilter'].append({'name': 'Condition',
                                                  'value': self.condition})

            # Search for listings
            response = self.api.execute('findItemsAdvanced', api_request)
            response = response.dict()

            # Return results
            items = response.get('searchResult').get('item')
            if items is not None:
                return items
            else:
                return []
        except ConnectionError as e:
            db_logger.error("{}  :  Exception in search_buy_it_now: {}".format(datetime.datetime.now(), e))
            try:
                print(e.response.dict())
            except:
                pass

    def search_auctions(self):
        try:
            api_request = {
                'keywords': self.keywords,
                'itemFilter': [
                    {'name': 'FeedbackScoreMin',
                     'value': self.min_feedback},
                    {'name': 'MaxPrice',
                     'value': self.max_price.amount},
                    {'name': 'MinPrice',
                     'value': self.min_price.amount},
                    {'name': 'LocatedIn',
                     'value': self.located_in},
                    {'name': 'ListingType',
                     'value': 'Auction'},
                ],
                'sortOrder': 'EndTimeSoonest',
                'outputSelector': 'SellerInfo',
                'descriptionSearch': True
            }

            if self.condition is not 0:
                api_request['itemFilter'].append({'name': 'Condition',
                                                  'value': self.condition})

            # Search for listings
            response = self.api.execute('findItemsAdvanced', api_request)
            response = response.dict()

            # Return results
            items = response.get('searchResult').get('item')
            if items is not None:
                return items
            else:
                return []
        except ConnectionError as e:
            db_logger.error("{}  :  Exception in search_auctions: {}".format(datetime.datetime.now(), e))
            try:
                print(e.response.dict())
            except:
                pass

    def get_single_item(self, item_id):
        self.connect("Shopping")
        try:
            api_request = {
                'ItemID': item_id,
                'IncludeSelector': ['Description']
            }
            response = self.api.execute('GetSingleItem', api_request)
            print("EndTime: %s" % response.reply.Item.EndTime)

            response = response.dict()
            # Return results
            return response.get('Item')

        except ConnectionError as e:
            db_logger.exception("{}  :  Exception in get_single_item: {}".format(datetime.datetime.now(), e))
            try:
                print(e.response.dict())
            except:
                pass


class EbayItem(models.Model):
    EDITABLE_FIELDS = ['name', 'description', 'start_time', 'end_time', 'listing_type', 'price', 'url', 'insert_date']
    DISPLAY_FIELDS = ['item_id', 'name', 'description', 'start_time', 'end_time', 'listing_type', 'price', 'url',
                      'insert_date']

    item_id = models.BigIntegerField()
    name = models.CharField(max_length=500)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    listing_type = models.CharField(max_length=20)
    auction_or_fixed = models.CharField(max_length=1)
    price = MoneyField(
        decimal_places=2,
        default=0,
        default_currency='GBP',
        max_digits=11,
    )
    image = models.CharField(max_length=300)
    url = models.CharField(max_length=300)
    seller_feedback = models.IntegerField()
    passed_filter = models.BooleanField(default=True)
    insert_date = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(default=False)

    # MANAGERS
    objects = models.Manager()

    # META CLASS
    class Meta:
        verbose_name = 'Ebay Item'
        verbose_name_plural = 'Ebay Items'

    # TO STRING METHOD
    def __str__(self):
        return '{}'.format(self.name)

    # SAVE METHOD
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Call the "real" save() method.

    # OTHER METHODS
    def is_recent(self, max_mins):
        try:
            then = self.start_time
            now_naive = datetime.datetime.utcnow()
            now = now_naive.replace(tzinfo=pytz.utc)
            # now = datetime.datetime.now()
            diff = now - then
            duration_seconds = diff.total_seconds()
            minutes = divmod(duration_seconds, 60)[0]

            if minutes < max_mins:
                return True
            else:
                return False
        except ConnectionError as e:
            db_logger.exception("{}  :  Exception in is_recent: {}".format(datetime.datetime.now(), e))
            try:
                print(e.response.dict())
            except:
                pass

    def is_ending_soon(self, max_mins):
        try:
            then = self.end_time
            now_naive = datetime.datetime.utcnow()
            now = now_naive.replace(tzinfo=pytz.utc)
            # now = datetime.datetime.now()
            diff = then - now
            duration_seconds = diff.total_seconds()
            minutes = divmod(duration_seconds, 60)[0]

            if minutes < max_mins:
                return True
            else:
                return False
        except ConnectionError as e:
            db_logger.exception("{}  :  Exception in is_ending_soon: {}".format(datetime.datetime.now(), e))
            try:
                print(e.response.dict())
            except:
                pass

    def filter_anti_keywords(self, text, anti_keywords: str):
        try:
            anti_keywords_list = anti_keywords.split(',')
            for anti in anti_keywords_list:
                if anti.lower() in text.lower().strip('\n'):
                    db_logger.info(
                        "{}  :  Filtered out anti keyword [{}] from item [{}]".format(datetime.datetime.now(), anti,
                                                                                      str(text)))
                    print(
                        "{}  :  Filtered out anti keyword [{}] from item [{}]".format(datetime.datetime.now(), anti,
                                                                                      str(text)))
                    return False

            return True
        except ConnectionError as e:
            db_logger.exception("{}  :  Exception in filter_anti_keywords: {}".format(datetime.datetime.now(), e))
            try:
                print(e.response.dict())
            except:
                pass

    def filter_item(self, wanted_item: WantedItem):
        try:
            # Filter out ebay power sellers (feedback > 1000ish)
            if self.seller_feedback < wanted_item.min_feedback or self.seller_feedback > wanted_item.max_feedback:
                return False

            if self.auction_or_fixed == 'F':
                # Check if it was recent
                good_item = self.is_recent(wanted_item.buy_it_now_time)
                if not good_item:
                    return False
                # Check against our anti keywords to filter out junk
                good_item = self.filter_anti_keywords(self.name, wanted_item.anti_keywords)
                if not good_item:
                    return False

            elif self.auction_or_fixed == 'A':
                # Check if it is ending soon
                good_item = self.is_ending_soon(wanted_item.auction_alert_time)
                if not good_item:
                    return False
                # Check against our anti keywords to filter out junk
                good_item = self.filter_anti_keywords(self.name, wanted_item.anti_keywords)
                if not good_item:
                    return False

            # Get Single item
            details = wanted_item.get_single_item(self.item_id)

            # Check anti keywords not in description
            self.description = html2text.html2text(details.get('Description'))
            # Check our description against anti keywords to filter out junk
            good_item = self.filter_anti_keywords(self.description, wanted_item.anti_keywords)
            if not good_item:
                return False

            # All checks passed, return True
            return True

        except ConnectionError as e:
            db_logger.exception("{}  :  Exception in filter_item: {}".format(datetime.datetime.now(), e))
            try:
                print(e.response.dict())
            except:
                pass

    def send_alert(self, wanted_item: WantedItem):
        try:
            print("sending alert for item: {}".format(self.url))
            db_logger.info("Sending alert for item: {}".format(self.url))

            notification_routes = wanted_item.notifications.all()
            for notification_route in notification_routes:
                # Send an alert for each notification route.
                notification_route: NotificationRoute
                split = notification_route.webhook.split('/')
                if notification_route.type == 'DIS':
                    id = split[5]
                    token = split[6]
                    # Create webhook
                    webhook = discord.Webhook.partial(id,
                                                      token,
                                                      adapter=discord.RequestsWebhookAdapter())

                    date_time_str = datetime.datetime.now()
                    if type(date_time_str) == str:
                        date_time_obj = datetime.datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                    else:
                        date_time_obj = date_time_str

                    start_time = utc_to_local(self.start_time)
                    end_time = utc_to_local(self.end_time)

                    # Build the embed
                    if notification_route.include_item_description:
                        embed = discord.Embed(title=self.name, description=self.description, color=0x00ff00)
                    else:
                        embed = discord.Embed(title=self.name, color=0x00ff00)
                    # embed.add_field(name='Description', value=self.description, inline=True)
                    embed.add_field(name='Price', value='£' + str(self.price.amount), inline=True)
                    embed.add_field(name='Type', value=self.listing_type, inline=True)
                    embed.add_field(name=":date: Time of Alert", value=date_time_obj.strftime("%d/%m/%Y  %H:%M %Z"),
                                    inline=True)
                    embed.add_field(name=':date: Start Time', value=start_time.strftime("%d/%m/%Y  %H:%M %Z"),
                                    inline=True)
                    embed.add_field(name=':date: End Time', value=end_time.strftime("%d/%m/%Y  %H:%M %Z"), inline=True)
                    embed.add_field(name='URL', value=self.url, inline=True)
                    embed.set_image(url=self.image)

                    # Send it
                    webhook.send(embed=embed)

                elif notification_route.type == 'EMA':
                    me = 'alert@ebayflipper.com'
                    to = notification_route.webhook
                    # Email notification
                    msg = MIMEText(self.url)
                    msg['Subject'] = 'New Item Alert - {}'.format(self.name)
                    msg['From'] = me
                    msg['To'] = to

                    # Send the message via our own SMTP server, but don't include the
                    # envelope header.
                    s = smtplib.SMTP('localhost')
                    s.sendmail(me, [to], msg.as_string())
                    s.quit()

                else:
                    # TODO: Slack webhook parse
                    pass

        except ConnectionError as e:
            db_logger.exception("{}  :  Exception in send_alert: {}".format(datetime.datetime.now(), e))
            try:
                print(e.response.dict())
            except:
                pass
