from background_task import background
from django.contrib.auth.models import User
from .models import WantedItem, NotificationRoute, EbayItem
import discord

import logging

logger = logging.getLogger(__name__)
from datetime import timezone, datetime


# @background(schedule=60)
def notify_user():
    # lookup user by id and send them a message
    notification_routes = NotificationRoute.objects.all()
    for notification_route in notification_routes:
        notification_route: NotificationRoute
        # https://discordapp.com/api/webhooks//
        split = notification_route.webhook.split('/')
        if notification_route.type == 'DIS':
            id = split[5]
            token = split[6]
        else:
            # TODO: Slack webhook parse
            id = split[5]
            token = split[6]

        # Create webhook
        webhook = discord.Webhook.partial(id,
                                          token,
                                          adapter=discord.RequestsWebhookAdapter())

        # Build the embed
        embed = discord.Embed(title="D", description="TESTER", color=0x00ff00)

        # Send it
        webhook.send(embed=embed)


# TODO: Later do multithreading
def search_and_filter(wanted_item: WantedItem):
    # Connect to API
    wanted_item.connect()

    # List to hold all Ebay Items
    wanted_item.found_items = []

    # Search for latest buy it now / fixed price deals
    buy_it_now_items = wanted_item.search_buy_it_now()
    for item in buy_it_now_items:
        # Check if we have already found and sent this.
        try:
            already_found = EbayItem.objects.get(item_id=item['itemId'])
        except Exception as e:
            # New item, continue
            # Prepare Item
            time_started = datetime.strptime(item['listingInfo']['startTime'],
                                             '%Y-%m-%dT%H:%M:%S.%fZ')
            time_started = time_started.replace(tzinfo=timezone.utc)
            time_ending = datetime.strptime(item['listingInfo']['endTime'],
                                            '%Y-%m-%dT%H:%M:%S.%fZ')
            time_ending = time_ending.replace(tzinfo=timezone.utc)

            ebay_item = EbayItem(item_id=item['itemId'], name=item['title'], description='', start_time=time_started,
                                 end_time=time_ending, listing_type=item['listingInfo']['listingType'],
                                 auction_or_fixed='F',
                                 price=item['sellingStatus']['currentPrice']['value'], image=item['galleryURL'],
                                 url=item['viewItemURL'], seller_feedback=int(item['sellerInfo']['feedbackScore']))

            wanted_item.found_items.append(ebay_item)

    # Search for latest Auction Deals
    auction_items = wanted_item.search_auctions()
    for item in auction_items:
        # Check if we have already found and sent this.
        try:
            already_found = EbayItem.objects.get(item_id=item['itemId'])
        except Exception as e:
            # New item, continue
            # Prepare Item
            time_started = datetime.strptime(item['listingInfo']['startTime'],
                                             '%Y-%m-%dT%H:%M:%S.%fZ')
            time_started = time_started.replace(tzinfo=timezone.utc)
            time_ending = datetime.strptime(item['listingInfo']['endTime'],
                                            '%Y-%m-%dT%H:%M:%S.%fZ')
            time_ending = time_ending.replace(tzinfo=timezone.utc)

            ebay_item = EbayItem(item_id=item['itemId'], name=item['title'], description='', start_time=time_started,
                                 end_time=time_ending, listing_type=item['listingInfo']['listingType'],
                                 auction_or_fixed='A',
                                 price=item['sellingStatus']['currentPrice']['value'], image=item['galleryURL'],
                                 url=item['viewItemURL'], seller_feedback=int(item['sellerInfo']['feedbackScore']))

            wanted_item.found_items.append(ebay_item)

    # Filter Auction and Fixed Price items and then send alerts to Discord
    for item in wanted_item.found_items:
        item: EbayItem

        passed_filter = item.filter_item(wanted_item)

        if passed_filter:
            # Add to list of found items. (save to database)
            item.save()

            # Send alert to discord.
            item.send_alert(wanted_item)


# @background(schedule=60) # Every minute
def scan_ebay_items():
    try:
        logger.info("Scanning items...")

        # Get Wanted Items
        wanted_items = WantedItem.objects.filter(deleted=False)

        for wanted_item in wanted_items:
            search_and_filter(wanted_item)

        logger.info("Finished scanning items...")


    except Exception as e:
        print(e)
        logger.error('There was an error, with a stack trace!', exc_info=True)
