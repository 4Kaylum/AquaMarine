import discord
import utils
import random
import asyncio
from discord.ext import commands


class Fishing(commands.Cog):
    def __init__(self, bot:commands.AutoShardedBot):
        self.bot = bot
        self.fish = bot.fish
        self.current_fishers = []
    
    
    @commands.command(aliases=["bal"])
    @commands.bot_has_permissions(send_messages=True)
    async def balance(self, ctx:commands.Context):
        async with utils.DatabaseConnection() as db:
            fetched = await db("""SELECT * FROM user_balance WHERE user_id = $1""", ctx.author.id)
        
        if not fetched:
            return await ctx.send("You have no money!")
        await ctx.send(f"You have {fetched[0]['balance']} money!")
    
    
    @commands.command(aliases=["bucket"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def fishbucket(self, ctx:commands.Context, user:discord.Member = None):
        user = user or ctx.author
        
        async with utils.DatabaseConnection() as db:
            fetched = await db("""SELECT * FROM user_fish_inventory WHERE user_id = $1""", user.id)
        
        if not fetched:
            if user == ctx.author:
                return await ctx.send("You have no fish in your bucket!")
            return await ctx.send(f"{user.display_name} has no fish in their bucket!")
        
        embed = discord.Embed()
        embed.title = f"{user.display_name}'s fish bucket"
        
        for i in fetched:
            embed.add_field(name=i['fish_name'], value=f"This fish is a **{' '.join(i['fish'].split('_')).title()}**", inline=False)
            
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def fish(self, ctx:commands.Context):
        if ctx.author.id in self.current_fishers:
            return await ctx.send(f"{ctx.author.display_name}, you're already fishing!")
        
        self.current_fishers.append(ctx.author.id)
        
        rarity = random.choices(
            ["common", "uncommon", "rare", "epic", "legendary", "mythic",],
            [.6689, .2230, .0743, .0248, .0082, .0008,])[0]
        
        new_fish = random.choice(list(self.fish[rarity].values()))
        
        embed = discord.Embed()
        embed.title = f"You caught a {rarity} {new_fish['name']}!"
        embed.set_image(url="attachment://new_fish.png")
        
        fish_file = discord.File(new_fish["image"], "new_fish.png")
        message = await ctx.send(file=fish_file, embed=embed)
        
        emojis = [844237901105594378, 844245357298450432]
        gen = (x for x in self.bot.emojis if x.id in emojis)
        for i in gen:
            await message.add_reaction(i)
        
        check = lambda reaction, user: reaction.emoji.id in emojis and user.id == ctx.author.id and reaction.message.id == message.id
        try:
            choice = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            choice = "sell" if choice[0].emoji.id == 844237901105594378 else "keep"
        except asyncio.TimeoutError:
            await ctx.send("Did you forget about me? I've been waiting for a while now! I'll just assume you wanted to sell the fish.")
            choice = "sell"
        
        if choice == "sell":
            async with utils.DatabaseConnection() as db:
                await db("""
                    INSERT INTO user_balance (user_id, balance) VALUES ($1, $2)
                    ON CONFLICT (user_id) DO UPDATE SET balance = user_balance.balance + $2;
                    """, ctx.author.id, new_fish["cost"])
                self.current_fishers.remove(ctx.author.id)
            return await ctx.send(f"Sold your **{new_fish['name']}** for **{new_fish['cost']}**!")
        
        await ctx.send("What do you want to name your new fish? (32 character limit)")
        check = lambda m: m.author == ctx.author and m.channel == ctx.channel and len(m.content) <= 32
        
        try:
            name = await self.bot.wait_for("message", timeout=60.0, check=check)
            name = name.content
            return await ctx.send(f"You're new fish **{name}** has been added to your bucket!")
        
        except asyncio.TimeoutError:
            name = f"{random.choice(['Captain', 'Mr.', 'Mrs.', 'Commander'])} {random.choice(['Nemo', 'Bubbles', 'Jack', 'Finley', 'Coral'])}"
            return await ctx.send(f"Did you forget about me? I've been waiting for a while now! I'll name the fish for you. Let's call it **{name}**")
        
        finally:
            async with utils.DatabaseConnection() as db:
                await db("""INSERT INTO user_fish_inventory (user_id, fish, fish_name) VALUES ($1, $2, $3)""", ctx.author.id, new_fish["raw_name"], name)
            self.current_fishers.remove(ctx.author.id)
    
    @commands.command()
    @commands.is_owner()
    async def freset(self, ctx:commands.Context):
        self.current_fishers = []
        await ctx.message.add_reaction('👌')

def setup(bot):
    bot.add_cog(Fishing(bot))