"""Mix.py"""
import json
import sys
import textwrap
import traceback
from asyncio import sleep
from base64 import b64encode
from contextlib import redirect_stdout
from datetime import datetime
from io import BytesIO, StringIO
from os import environ, listdir, remove, system
from random import choice, randint, uniform
from typing import Optional

from aiohttp import ClientSession
from discord import File
from discord.ext.commands import Cog, command, is_owner
from pytz import timezone

from War import War
import utils
from Converters import Country, Id, IsMyNick, Quality


class Mix(Cog):
    """Mix Commands"""

    def __init__(self, bot):
        self.bot = bot

    @command()
    async def party(self, ctx, party: Optional[Id] = 0, *, nick: IsMyNick):
        """Joins a party.
        Do not provide party if you want it to auto-apply to the first party.
        For leaving party, send a negative party id."""
        server = ctx.channel.name
        base_url = f"https://{server}.e-sim.org/"
        if party < 0:
            return await self.bot.get_content(base_url + "partyStatistics.html", data={"action": "LEAVE", "submit": "Leave party"})
        if party == 0:
            tree = await self.bot.get_content(base_url + "partyStatistics.html?statisticType=MEMBERS", return_tree=True)
            party = utils.get_ids_from_path(tree, '//*[@id="esim-layout"]//table//tr[2]//td[3]/')[0]
        party_payload = {"action": "JOIN", "id": party, "submit": "Join"}
        url = await self.bot.get_content(base_url + "partyStatistics.html", data=party_payload)
        await ctx.send(f"**{nick}** <{url}>")

    @command()
    async def candidate(self, ctx, delay: Optional[float] = 0, *, nick: IsMyNick):
        """Candidate for congress / president elections.
        It will also auto join to the first party (by members) if necessary."""
        server = ctx.channel.name
        base_url = f"https://{server}.e-sim.org/"
        if delay:
            await ctx.send(f"**{nick}** Ok. If you changed your mind, type `.cancel candidate {nick}`")
            await sleep(delay)
        if utils.should_break(ctx):
            return
        today = int(datetime.now().astimezone(timezone('Europe/Berlin')).strftime("%d"))  # game time
        if 1 < today < 5:
            payload = {"action": "CANDIDATE", "presentation": "http://", "submit": "Candidate for president"}
            link = "presidentalElections.html"
        elif 20 < today < 24:
            payload = {"action": "CANDIDATE", "presentation": "http://", "submit": "Candidate for congress"}
            link = "congressElections.html"
        else:
            return await ctx.send(f"**{nick}** ERROR: I can't candidate today. Try another time.")

        try:
            await ctx.invoke(self.bot.get_command("party"), nick=nick)
        except Exception:
            pass
        url = await self.bot.get_content(base_url + link, data=payload)
        await ctx.send(f"**{nick}** <{url}>")

    @command()
    async def avatar(self, ctx, *, nick):
        """
        Change avatar img.
        If you don't want the default img, write it like that:
        `.avatar https://picsum.photos/150, Your Nick` (with a comma)"""

        if "," in nick:
            img_url, nick = nick.split(",")
        else:
            img_url = "https://source.unsplash.com/random/150x150"
        await IsMyNick().convert(ctx, nick)
        server = ctx.channel.name
        base_url = f"https://{server}.e-sim.org/"
        async with ClientSession() as session:
            async with session.get(img_url.strip()) as resp:
                avatar_base64 = str(b64encode((BytesIO(await resp.read())).read()))[2:-1]

        payload = {"action": "CONTINUE", "v": f"data:image/png;base64,{avatar_base64}",
                   "h": "none", "e": "none", "b": "none", "a": "none", "c": "none", "z": 1, "r": 0,
                   "hh": 1, "eh": 1, "bh": 1, "ah": 1, "hv": 1, "ev": 1, "bv": 1, "av": 1, "act": ""}
        url = await self.bot.get_content(base_url + "editAvatar.html", data=payload)
        await ctx.send(f"**{nick}** <{url}>")

    @command()
    async def missions(self, ctx, *, nick: IsMyNick):
        """Auto finish missions.
        If you want to skip a mission, type:
        .click "nick" https://secura.e-sim.org/betaMissions.html {"action": "SKIP"}
        You can also use {"action": "COMPLETE"} and {"action": "START"}
        """
        server = ctx.channel.name
        base_url = f"https://{server}.e-sim.org/"

        await ctx.send(f"**{nick}** Ok sir! If you want to stop it, type `.cancel missions {nick}`")
        prv_num = 0
        for _ in range(30):
            if utils.should_break(ctx):
                break
            await self.bot.get_content(base_url + "betaMissions.html", data={"action": "COMPLETE"})
            tree = await self.bot.get_content(base_url, return_tree=True)
            my_id = utils.get_ids_from_path(tree, '//*[@id="userName"]')[0]
            try:
                num = int(str(tree.xpath('//*[@id="inProgressPanel"]/div[1]/div/strong')[0].text).split("#")[1])
            except Exception:
                if tree.xpath('//*[@id="missionDropdown"]//div[2]/text()'):
                    return await ctx.send(f"**{nick}** You have completed all your missions for today, come back tomorrow!")
                continue
            if prv_num == num:
                return await ctx.send(f"**{nick}** ERROR: Couldn't complete mission #{num}.\n" +
                                      f'Consider skipping it: `.click {nick} {base_url}betaMissions.html {"action": "SKIP", "submit": "Skip"}`')
            await ctx.send(f"**{nick}** Mission number {num}")
            c = await self.bot.get_content(base_url + "betaMissions.html", data={"action": "START"})
            if "MISSION_START_OK" not in c:
                c = await self.bot.get_content(base_url + "betaMissions.html", data={"action": "COMPLETE"})
            """Day 1:
            Mission #1: First training.
            Mission #2: Your first job.
            Mission #3: First day of work.
            Mission #4: Fight 1 hit.
            Mission #5: Restore your health points.
            Mission #6: Travel to the capital.
            Mission #7: Check your notifications page.
            Mission #8: Buy some products.
            Mission #9 Achievements.
            
            Day 2:
            Mission #10 Second work.
            Mission #11 Second train.
            Mission #12 Buy gold.
            Mission #13 Bid auction.
            Mission #14 Sell equipment on auction.
            Mission #15 Sell 100 grain.
            Mission #16 Fight with weps. (1 hit, Q1 wep).
            Mission #17 Buy at least one Q1 weapon.
            Mission #18 Change background.
            Mission #19: Deal 10,000 damage.
            
            Day 3:
            Mission #20 Third work.
            Mission #21 Third train.
            Mission #22 BERSERK.
            Mission #23 Deal 30,000 damage
            Mission #24 Send application to Military Unit 
            Mission #25 Bid auction.
            Mission #26 BERSERK.
            
            Day 4:
            Mission #27 work + train.
            Mission #28 Deal 2 critical hits.
            Mission #29 Add a friend.
            Mission #30 Deal berserk with weapons
            Mission #31 Comment an article
            Mission #32 Join a party
            
            Day 5:
            Mission #33 work + train.
            Mission #34 Get total 450 XP.
            Mission #35: Comment a shout
            Mission #36: Buy steroids
            Mission #37: Fight five times
            Mission #38: Deplete limits
            Mission #39: Wear EQ.
            Mission #40: Vote a shout
            
            Day 6:
            Mission #41: Train and fight (1 hit)
            Mission #42: Travel abroad
            Mission #43: Fight for foreign country
            Mission #44: Come back home
            Mission #45: Send reflink to a friend
            Mission #46: Motivate someone
            Mission #47: Write a private message
            Mission #48: Subscribe a newspaper"""
            if num == 1:
                await self.bot.get_content(base_url + "inboxMessages.html")
                await self.bot.get_content(base_url + "train/ajax", data={"action": "train"})
            elif num == 2:
                await ctx.invoke(self.bot.get_command("job"), nick=nick)
            elif num in (3, 10, 20, 27, 33):
                await ctx.invoke(self.bot.get_command("work"), nick=nick)
            elif num in (11, 21):  # train
                pass
            elif num in (4, 16, 28, 37):
                tree = await self.bot.get_content(f'{base_url}battle.html?id=0', return_tree=True)
                for _ in range(1 if num != 28 else 5):
                    fight_url, data = await War.get_fight_data(base_url, tree, 0 if num != 16 else 1, choice(["default", "attacker"]),
                                                               "Regular" if num != 37 else "Berserk")
                    await self.bot.get_content(fight_url, data=data)
            elif num == 5:
                await self.bot.get_content(f"{base_url}eat.html", data={'quality': 1})
            elif num == 6:
                citizen = await self.bot.get_content(f'{base_url}apiCitizenById.html?id={my_id}')
                capital = [row['id'] for row in await self.bot.get_content(base_url + "apiRegions.html") if row[
                    'homeCountry'] == citizen['citizenshipId'] and row['capital']][0]
                await ctx.invoke(self.bot.get_command("fly"), capital, 5, nick=nick)
            elif num == 7:
                await self.bot.get_content(base_url + "notifications.html")
            elif num == 8:
                tree = await self.bot.get_content(f"{base_url}productMarket.html", return_tree=True)
                product_id = tree.xpath('//*[@class="buy"]/button')[0].attrib['data-id']
                payload = {'action': "buy", 'id': product_id, 'quantity': 1, "submit": "Buy"}
                await self.bot.get_content(base_url + "productMarket.html", data=payload)
            elif num == 9:
                # await self.bot.get_content(base_url + 'friends.html?action=PROPOSE&id=8')
                await self.bot.get_content(base_url + "citizenAchievements.html",
                                           data={"id": my_id, "submit": "Recalculate achievements"})

            # day 2
            elif num == 12:
                tree = await self.bot.get_content(f"{base_url}monetaryMarket.html?buyerCurrencyId=0", return_tree=True)
                try:
                    offer_id = tree.xpath("//*[@class='buy']/button")[0].attrib['data-id']
                    payload = {'action': "buy", 'id': offer_id, 'ammount': 0.01, "submit": "OK"}
                    await self.bot.get_content(base_url + "monetaryMarket.html", data=payload)
                except IndexError:
                    await ctx.send(f"**{nick}** ERROR: couldn't buy gold")
            elif num in (13, 25):
                tree = await self.bot.get_content(f"{base_url}auctions.html?type=EQUIPMENT&eqQ_Q1=true", return_tree=True)
                auction = tree.xpath('//*[@class="auctionButtons"]/button')[1]
                payload = {'action': "BID", 'id': auction.attrib['data-id'], 'price': auction.attrib['data-minimal-outbid']}
                url = await self.bot.get_content(base_url + "auctionAction.html", data=payload)
                await ctx.send(f"**{nick}** <{url}>")
            elif num == 14:
                tree = await self.bot.get_content(base_url + 'storage.html?storageType=EQUIPMENT', return_tree=True)
                item_id = tree.xpath('//*[starts-with(@id, "cell")]/a/text()')[-1].replace("#", "")
                await ctx.invoke(self.bot.get_command("auction"), item_id, 0.01, 24, nick=nick)
            elif num == 15:
                citizen = await self.bot.get_content(f'{base_url}apiCitizenById.html?id={my_id}')
                payload = {'product': "GRAIN", 'countryId': citizen['citizenshipId'], 'storageType': "PRODUCT",
                           "action": "POST_OFFER", "price": 0.1, "quantity": 100}
                sell_grain = await self.bot.get_content(base_url + "storage.html", data=payload)
                await ctx.send(f"**{nick}** <{sell_grain}>")
            elif num == 17:
                tree = await self.bot.get_content(f"{base_url}productMarket.html?resource=WEAPON&quality=1&countryId=-1", return_tree=True)
                product_id = tree.xpath('//*[@class="buy"]/button')[0].attrib['data-id']
                payload = {'action': "buy", 'id': product_id, 'quantity': 1, "submit": "Buy"}
                await self.bot.get_content(base_url + "productMarket.html", data=payload)
            elif num == 18:
                payload = {'setBg': choice(["AR", "CL", "CH", "DN", "EE", "HUN"]), 'action': "CHANGE_BACKGROUND"}
                await self.bot.get_content(base_url + "editCitizen.html", data=payload)
            elif num in (19, 22, 23, 26):
                if num in (22, 26):
                    restores = 1
                else:
                    restores = 2
                    await ctx.send(f"**{nick}** Hitting {restores} restores, it might take a while")
                await ctx.invoke(self.bot.get_command("auto_fight"), nick, chance_to_skip_restore=0, restores=restores)

            # Day 3:
            elif num == 24:
                ctx.invoked_with = "mu"
                await ctx.invoke(self.bot.get_command("citizenship"), "Mission " * randint(10, 15), randint(1, 21), nick=nick)

            # Day 4:
            elif num == 29:
                await self.bot.get_content(base_url + f'friends.html?action=PROPOSE&id={randint(1, my_id)}')
                await ctx.invoke(self.bot.get_command("friends"), nick=nick)
            elif num == 30:
                tree = await self.bot.get_content(f'{base_url}battle.html?id=0', return_tree=True)
                fight_url, data = await War.get_fight_data(base_url, tree, 1, choice(["default", "attacker"]), "Berserk")
                await self.bot.get_content(fight_url, data=data)
            elif num == 31:
                for _ in range(10):
                    payload = {"action": "NEW", "key": f"Article {randint(1, 40)}", "submit": "Publish",
                               "body": choice(["Mission", "Hi", "Hello there", "hello", "Discord?"])}
                    comment = await self.bot.get_content(base_url + "comment.html", data=payload)
                    if "MESSAGE_POST_OK" in comment:
                        break
            elif num == 32:
                try:
                    tree = await self.bot.get_content(base_url + "partyStatistics.html?statisticType=MEMBERS",
                                                      return_tree=True)
                    party_id = utils.get_ids_from_path(tree, '//*[@id="esim-layout"]//table//tr[2]//td[3]/')[0]
                    payload1 = {"action": "JOIN", "id": party_id, "submit": "Join"}
                    b = await self.bot.get_content(base_url + "partyStatistics.html", data=payload1)
                    await ctx.send(f"**{nick}** <{b}>")
                except Exception:
                    await ctx.send(f"**{nick}** couldn't join a party")

            # Day 5:
            elif num == 34:  # 450 xp
                pass
            elif num == 35:
                await self.bot.get_content(base_url + f"replyToShout.html?id={randint(1, 101)}",
                                           data={"body": choice(["OK", "Whatever", "Thanks", "Discord?", "Mission"]),
                                                 "submit": "Shout!"})
            elif num == 36:
                payload = {'itemType': "STEROIDS", 'storageType': "SPECIAL_ITEM", 'action': "BUY", "quantity": 1}
                await self.bot.get_content(base_url + "storage.html", data=payload)
            elif num == 38:
                tree = await self.bot.get_content(f'{base_url}battle.html?id=0', return_tree=True)
                fight_url, data = await War.get_fight_data(base_url, tree, 0, choice(["default", "attacker"]), "Berserk")
                for _ in range(5):
                    await self.bot.get_content(fight_url, data=data)
                for _ in range(10):
                    await self.bot.get_content(f"{base_url}eat.html", data={'quality': 1})
                for _ in range(5):
                    await self.bot.get_content(fight_url, data=data)
                for _ in range(10):
                    await self.bot.get_content(f"{base_url}gift.html", data={'quality': 1})
                for _ in range(5):
                    await self.bot.get_content(fight_url, data=data)
            elif num == 39:
                tree = await self.bot.get_content(base_url + 'storage.html?storageType=EQUIPMENT', return_tree=True)
                item_id = tree.xpath('//*[starts-with(@id, "cell")]/a/text()')[0].replace("#", "")
                payload = {'action': "EQUIP", 'itemId': item_id}
                await self.bot.get_content(base_url + "equipmentAction.html", data=payload)
            elif num == 40:
                await self.bot.get_content(f"{base_url}shoutVote.html", data={"id": randint(1, 100), "vote": 1})

            elif num == 41:
                await ctx.invoke(self.bot.get_command("work"), nick=nick)
                tree = await self.bot.get_content(f"{base_url}battles.html?countryId=-1", return_tree=True)
                battle_ids = utils.get_ids_from_path(tree, '//*[@class="battleHeader"]//a')
                await ctx.invoke(self.bot.get_command("fight"), nick, battle_ids[0], choice(["defender", "attacker"]), 0, 1, 5)
            elif num in (42, 43):
                pass
            elif num == 44:
                citizen = await self.bot.get_content(f'{base_url}apiCitizenById.html?id={my_id}')
                region = [x["id"] for x in await self.bot.get_content(f'{base_url}apiRegions.html') if x["homeCountry"] == citizen["citizenshipIs"]]
                await ctx.invoke(self.bot.get_command("fly"), choice(region), 5, nick=nick)
            elif num == 45:
                async with ClientSession(headers={"User-Agent": environ["headers"]}) as session:
                    async with session.get(f"{base_url}lan.{my_id}/", ssl=True) as _:
                        pass
            elif num == 46:
                await ctx.invoke(self.bot.get_command("motivate"), nick=nick)

            elif num == 47:
                citizen = await self.bot.get_content(f'{base_url}apiCitizenById.html?id={my_id}')
                payload = {'receiverName': f"{citizen['citizenship']} Org", "title": "Hi",
                           "body": choice(["Hi", "Can you send me some gold?", "Hello there!", "Discord?"]),
                           "action": "REPLY", "submit": "Send"}
                await self.bot.get_content(base_url + "composeMessage.html", data=payload)
            elif num == 48:
                await self.bot.get_content(f"{base_url}sub.html", data={"id": randint(1, 21)})

            # Old missions:
            # new avatar:
            #    await self.bot.get_content(base_url + "editCitizen.html")
            # Check map:
            #    await self.bot.get_content(base_url + "newMap.html")
            # Shout:
            #    shout_body = choice(["Mission: Say hello", "Hi", "Hello", "Hi guys :)", "Mission"])
            #    payload = {'action': "POST_SHOUT", 'body': shout_body, 'sendToCountry': "on",
            #                "sendToMilitaryUnit": "on", "sendToParty": "on", "sendToFriends": "on"}
            #    await self.bot.get_content(f"{base_url}shoutActions.html", data=payload)
            # Vote article:
            #    await self.bot.get_content(f"{base_url}vote.html", data={"id": randint(1, 15)})
                """
            elif num == 29:
                for article_id in range(2, 7):
                    await self.bot.get_content(f"{base_url}vote.html", data={"id": article_id})

            elif num == 49:
                tree = await self.bot.get_content(base_url + 'storage.html?storageType=EQUIPMENT', return_tree=True)
                item_id = tree.xpath('//*[starts-with(@id, "cell")]/a/text()')[0].replace("#", "")
                payload = {'action': "EQUIP", 'itemId': item_id.replace("#", "")}
                await self.bot.get_content(base_url + "equipmentAction.html", data=payload)


            elif num == 60:
                await ctx.invoke(self.bot.get_command("friends"), nick=nick)
            elif num == 63:
                await self.bot.get_content(f"{base_url}medkit.html", data={})
                # if food & gift limits >= 10 it won't work.
            """
            else:
                await ctx.send(f"**{nick}** ERROR: I don't know how to finish this mission ({num}).")
            await sleep(uniform(1, 5))
            prv_num = num
        await ctx.send(f"**{nick}** missions command reached its end.")

    @command(aliases=["hospital"])
    async def building(self, ctx, region_id: Id, quality: Quality, at_round: int, *, nick: IsMyNick):
        """Proposing a building law (for presidents)"""
        base_url = f"https://{ctx.channel.name}.e-sim.org/"
        product_type = "DEFENSE_SYSTEM" if ctx.invoked_with.lower() == "building" else "HOSPITAL"
        payload = {'action': "PLACE_BUILDING", 'regionId': region_id, "productType": product_type,
                   "quality": quality, "round": at_round, 'submit': "Propose building"}
        url = await self.bot.get_content(base_url + "countryLaws.html", data=payload)
        await ctx.send(f"**{nick}** <{url}>")

    @command(hidden=True)
    async def config(self, ctx, key, value, *, nick: IsMyNick):
        """Examples:
            .config alpha Admin  my_nick
            .config alpha_password 1234  my_nick
            .config help ""  my_nick
        """
        if key == "trusted_users_ids":
            return await ctx.send(f"**{nick}** this is a sensitive key, so you will have to set it manually")
        with open(self.bot.config_file, "r", encoding="utf-8") as file:
            big_dict = json.load(file)
        if not value and key in big_dict:
            del big_dict[key]
            del environ[key]
            await ctx.send(f"I have deleted the `{key}` key from {nick}'s {self.bot.config_file} file")
            if key == "help":
                self.bot.remove_command("help")
        else:
            big_dict[key] = value
            environ[key] = value
            await ctx.send(f"I have added the following pair to {nick}'s {self.bot.config_file} file: `{key} = {value}`")
        with open(self.bot.config_file, "w", encoding="utf-8") as file:
            json.dump(big_dict, file)
        if key == "database_url":
            utils.initiate_db()
            for filename in listdir()[:]:
                if filename.endswith(".json") and "_" in filename:
                    server, collection = filename.replace(".json", "").split("_", 1)
                    with open(filename, "r", encoding='utf-8', errors='ignore') as file:
                        d = json.load(file)
                        for document, data in d.items():
                            await utils.replace_one(server, collection, document, data)
                    remove(filename)

    @command()
    async def register(self, ctx, lan, country: Country, *, nick: IsMyNick):
        """User registration.
        If you want to register with a different nick or password, see .help config"""
        server = ctx.channel.name
        base_url = f"https://{server}.e-sim.org/"
        headers = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 5.1.1; AFTM Build/LVY48F) CTV"}
        async with ClientSession(headers=headers) as session:
            async with session.get(base_url, ssl=True) as _:
                async with session.get(base_url + "index.html?advancedRegistration=true&lan=" + lan.replace(f"{base_url}lan.", ""), ssl=True) as _:
                    payload = {"login": nick, "password": environ.get(server+"_password", environ.get('password')), "mail": "",
                               "countryId": country, "checkHuman": "Human"}
                    async with session.post(base_url + "registration.html", data=payload, ssl=True) as registration:
                        if "act=register" not in str(registration.url):
                            await ctx.send(f"**{nick}** ERROR: Could not register")
                        else:
                            await ctx.send(f"**{nick}** <{registration.url}>\nHINT: type `.help avatar` and `.help missions`")

    @command()
    async def report(self, ctx, target_citizen: Id, category, report_reason, *, nick: IsMyNick):
        """Reporting a citizen.
        * The report_reason should be within quotes"""
        server = ctx.channel.name
        base_url = f"https://{server}.e-sim.org/"

        categories = ["STEALING_ORG", "POSSIBLE_MULTIPLE_ACCOUNTS", "AUTOMATED_SOFTWARE_OR_SCRIPTS", "UNPAID_DEBTS",
                      "SLAVERY", "EXPLOITING_GAME_MECHANICS", "ACCOUNT_SITTING", "PROFILE_CONTENT", "OTHER"]
        if category in categories:
            payload = {"id": target_citizen, 'action': "REPORT_MULTI", "ticketReportCategory": category,
                       "text": report_reason, "submit": "Report"}
            url = await self.bot.get_content(f"{base_url}ticket.html", data=payload)
            await ctx.send(f"**{nick}** <{url}>")
        else:
            await ctx.send(f"**{nick}** category can be one of:\n" + ", ".join(categories) + f"\n(not {category})")

    @command()
    async def elect(self, ctx, your_candidate, *, nick: IsMyNick):
        """Voting in congress / president elections."""
        server = ctx.channel.name
        base_url = f"https://{server}.e-sim.org/"
        today = int(datetime.now().astimezone(timezone('Europe/Berlin')).strftime("%d"))  # game time

        if today == 5:
            president = True
            link = "presidentalElections.html"
        elif today == 25:
            president = False
            link = "congressElections.html"
        else:
            return await ctx.send(f"**{nick}** ERROR: There are not elections today")

        tree = await self.bot.get_content(base_url + link, return_tree=True)
        payload = None
        for tr in range(2, 100):
            try:
                name = tree.xpath(f'//*[@id="esim-layout"]//tr[{tr}]//td[2]/a/text()')[0].strip()
            except IndexError:
                return await ctx.send(f"**{nick}** ERROR: No such candidate ({your_candidate})")
            if name.lower() == your_candidate.lower():
                try:
                    if president:
                        candidate_id = tree.xpath(f'//*[@id="esim-layout"]//tr[{tr}]/td[4]/form/input[2]')[0].value
                    else:
                        candidate_id = tree.xpath(f'//*[@id="esim-layout"]//tr[{tr}]//td[5]//*[@id="command"]/input[2]')[0].value
                except Exception:
                    return await ctx.send(f"**{nick}** ERROR: I couldn't find the vote button.")
                payload = {'action': "VOTE", 'candidate' if president else 'candidateId': candidate_id, "submit": "Vote"}
                break

        if payload:
            tree = await self.bot.get_content(base_url + link, data=payload, return_tree=True)
            msg = tree.xpath('//*[@id="esim-layout"]//div[1]/text()')
            await ctx.send(f"**{nick}** {' '.join(msg).strip() or 'voted'}")
        else:
            await ctx.send(f"**{nick}** candidate {your_candidate} was not found")

    @command()
    async def law(self, ctx, laws, your_vote, *, nick: IsMyNick):
        """Voting law(s).
        `ids` MUST be separated by a comma, and without spaces (or with spaces, but within quotes)
        Examples:
            .law 1,2,3   yes   my nick      (voting the laws with ids 1, 2, and 3)
            .law https://alpha.e-sim.org/law.html?id=1   no   my nick
        """
        server = ctx.channel.name
        base_url = f"https://{server}.e-sim.org/"
        if your_vote.lower() not in ("yes", "no"):
            return await ctx.send(f"**{nick}** ERROR: Parameter 'vote' can be 'yes' or 'no' only! (not {your_vote})")
        for law in laws.split(","):
            law = law.strip()
            link = f"{base_url}law.html?id={law}" if law.isdigit() else law

            payload = {'action': f"vote{your_vote.capitalize()}", "submit": f"Vote {your_vote.upper()}"}
            await self.bot.get_content(link)
            url = await self.bot.get_content(link, data=payload)
            await ctx.send(f"**{nick}** <{url}>")

    @command(aliases=["president"])
    async def revoke(self, ctx, citizen, *, nick: IsMyNick):
        """Proposing a revoke/elect president law.
        `ids` MUST be separated by a comma, and without spaces (or with spaces, but within quotes)
        Examples:
            .revoke  Admin  my nick
            .president "Admin News"   my nick
        """
        base_url = f"https://{ctx.channel.name}.e-sim.org/"
        if ctx.invoked_with.lower() == "revoke":
            payload = {"revokeLogin": citizen, "action": "REVOKE_CITIZENSHIP", "submit": "Revoke citizenship"}
        else:
            api_citizen = await self.bot.get_content(f"{base_url}apiCitizenByName.html?name={citizen.lower()}")
            payload = {"candidate": api_citizen["id"], "action": "ELECT_PRESIDENT", "submit": "Propose president"}
        await self.bot.get_content(base_url + "countryLaws.html")
        url = await self.bot.get_content(base_url + "countryLaws.html", data=payload)
        await ctx.send(f"**{nick}** <{url}>")

    @command()
    async def impeach(self, ctx, *, nick: IsMyNick):
        """Propose impeach"""
        base_url = f"https://{ctx.channel.name}.e-sim.org/"
        payload = {"action": "IMPEACHMENT", "submit": "Propose impeachment"}
        await self.bot.get_content(base_url + "countryLaws.html")
        url = await self.bot.get_content(base_url + "countryLaws.html", data=payload)
        await ctx.send(f"**{nick}** <{url}>")

    @command(hidden=True)
    async def click(self, ctx, nick: IsMyNick, link, *, data="{}"):
        """Clicks on a given link.
Examples:
.click "my nick" https://secura.e-sim.org/friends.html?action=PROPOSE&id=1   (GET request, not POST)
.click nick https://secura.e-sim.org/partyStatistics.html {"action": "LEAVE"}
.click nick https://secura.e-sim.org/myParty.html {"name": "XXX",  "description": "YYY", "action": "CREATE_PARTY"}
.click nick https://secura.e-sim.org/countryLaws.html {"action": "PROPOSE_DISMISS_MOF", "dismissMofLogin": "XXX"}
.click nick https://secura.e-sim.org/countryLaws.html {"action": "DONATE_MONEY_TO_COUNTRY_TREASURE", "currencyId": 0, "sum": 0.01, "reason": "X"}
.click nick https://secura.e-sim.org/countryLaws.html {"action": "LEAVE_COALITION"}
.click nick https://secura.e-sim.org/coalitionManagement.html {"action": "SUPPORT_CANDIDATE", "countryId": 0, "support": "positive"}
.click nick https://secura.e-sim.org/companies.html {"name": "XXX", "resource": "IRON"}
.click nick https://secura.e-sim.org/company.html {"action": "UPGRADE", "id": 1, "upgradeCompanybutton": "Upgrade company"}
.click nick https://secura.e-sim.org/company.html?id=1 {"price": 1.0, "action": "POST_JOB_OFFER"}
.click nick https://secura.e-sim.org/civilWar.html?id=1 {"action": "CAST_SUPPORT", "side": "Loyalists"}
.click nick https://secura.e-sim.org/countryLaws.html {"coalitionId": 1, "action": "JOIN_COALITION"}
.click nick https://secura.e-sim.org/stockCompanyAction.html {"currencyId": 0, "sum": 1, "id": 1, "reason": "", "action": "DONATE_MONEY"}
.click nick https://secura.e-sim.org/donateProducts.html?id=0000 {"product": "5-WEAPON", "quantity": 00000}
.click nick https://secura.e-sim.org/donateProductsToMilitaryUnit.html?id=0 {"product": "1-IRON", "quantity": 0}
.click nick https://secura.e-sim.org/promotionalCode.html {"code": "XXX", "action": "REDEEM"}
.click nick https://secura.e-sim.org/teamTournamentTeam.html?id=0 {"teamId": 0, "action": "APPLY"}
.click nick https://secura.e-sim.org/citizenshipApplicationAction.html {"action": "ACCEPT", "applicationId": 0}
"""
        url = await self.bot.get_content(link, data=json.loads(data.replace("'", '"')) or None)
        await ctx.send(f"**{nick}** <{url}>")

    @command(hidden=True)
    @is_owner()
    async def load(self, ctx, file: str) -> None:
        """Load Extensions"""
        self.bot.reload_extension(file)

    @command(hidden=True)
    async def execute(self, ctx, nick: IsMyNick, *, code) -> None:
        """Evaluates a given Python code.

        > **IMPORTANT**:  By default, anyone in your channel can use the command `execute` (including revealing your password!).
        > If you want to change it, add to your config file thr pair: `"trusted_users_ids": [00000, 11111],` ("Copy User ID" within Discord).
        > Only users in that list will be able to use `execute` (you can leave it empty)"""
        # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py#L215
        if ctx.author.id not in environ.get("trusted_users_ids", [ctx.author.id]):
            return
        server = ctx.channel.name
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message
        }

        env.update(globals())

        # remove ```py\n```
        if code.startswith('```') and code.endswith('```'):
            code = '\n'.join(code.split('\n')[1:-1])
        else:  # remove `foo`
            code = code.strip('` \n')

        to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'
        stdout = StringIO()
        try:
            exec(to_compile, env)
        except Exception as exc:
            return await ctx.send(f'```py\n{exc.__class__.__name__}: {exc}\n```')
        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                if ret is None:
                    if value:
                        await ctx.send(f'```py\n{value}\n```')
                else:
                    await ctx.send(f'```py\n{value}{ret}\n```')
            except Exception:
                io_output = StringIO(newline='')
                io_output.write(value + (ret or ""))
                io_output.seek(0)
                await ctx.send(file=File(fp=io_output, filename="output.txt"))

    @command(hidden=True)
    async def shutdown(self, ctx, restart: bool, *, nick: IsMyNick):
        """Shutting down specific nick.
        Warning: It's shutting down from all servers."""
        import platform
        for session in self.bot.sessions.values():
            await session.close()

        if restart:
            await ctx.send(f"**{nick}** attempting restart... (try `.ping {nick}` in a few seconds)")
            if platform.system() == 'Windows':
                system(f"start /b {sys.executable} bot.py")
            else:
                system(f"nohup {sys.executable} bot.py &")
        else:
            await ctx.send(f"**{nick}** shutting down...")
        await self.bot.close()

    @command(hidden=True)
    async def cancel(self, ctx, cmd: str, *, nick: IsMyNick):
        """Cancel command (it might take a while before it actually cancel)"""
        server = ctx.channel.name
        cmd = cmd.lower()
        if cmd not in self.bot.should_break_dict.get(server, {}):
            return await ctx.send(f"**{nick}** This command does not currently running. See `.running_commands {nick}`")
        self.bot.should_break_dict[server][cmd] = True
        await ctx.send(f"**{nick}** I have forwarded your instruction. (it might take a while until it actually cancel {cmd}). See also: `.running_commands {nick}`")
        if any(x in cmd for x in ("hunt-", "hunt_battle", "watch")):
            cmd = "auto_" + cmd
        if "auto_" in cmd:
            collection = cmd.split("_", 1)[-1].split("-")[0]
            data = await utils.find_one("auto", collection, environ['nick'])
            for command in data.get(ctx.channel.name, [])[:]:
                if command.get("command", cmd) == cmd:
                    data[ctx.channel.name].remove(command)
            await utils.replace_one("auto", collection, environ['nick'], data)

    @command(hidden=True)
    async def running_commands(self, ctx, *, nick: IsMyNick):
        await ctx.send(f"**{nick}** cancel any with `.cancel command {nick}`\n" +
                       "\n".join(cmd + (" (awaiting cancellation)" if status else "")
                                 for cmd, status in ctx.bot.should_break_dict.get(
                           ctx.channel.name, {}).items() if cmd not in ("cancel", "running_commands")))


def setup(bot):
    """setup"""
    bot.add_cog(Mix(bot))
