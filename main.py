import sys
import subprocess
import discord
from discord.ext import commands
import os
import random
import io
import asyncio
from datetime import datetime
from collections import defaultdict
import json
from database import add_invitation, get_top_inviters, get_invitation_count

warns_via_bot = set()

# === DISCORD BOT CONFIGURATION ===
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True


class MyBot(commands.Bot):
    async def setup_hook(self):
        # Charge les vues persistantes au démarrage
        self.add_view(VerifButton())
        self.add_view(TicketView())
        self.add_view(CloseButton())


        # Si tu as toujours le système de rappel de vote
        self.loop.create_task(vote_reminder())

bot = MyBot(command_prefix="!", intents=intents)

# === CONSTANTES ===
CATEGORY_IDS = {
    "illégal": 1400837942896885941,
    "legal": 1400838697775268002,
    "remboursement": 1400838778842513440,
    "candidature": 1400838818969423873,
    "wipe": 1400838858311991306,
    "mortrp": 1400838898665390213,
    "dévelopement": 1400838951417155736,
    "scènerp": 1400839015481086032,
}
VERIF_CHANNEL_ID = 1399517854675501111
CITOYEN_ROLE_ID = 1399517854142955682
STAFF_ROLE_ID = 1400835637313016031
LOG_CHANNEL_ID = 1399517856219140195
WARN_LOG_CHANNEL_ID = 1400837645139181739
WARN_ROLE_ID = 1400845159721209888
VOTE_CHANNEL_ID = 1400183110133350400 
LOG_GIVEAWAY_CHANNEL_ID = 1399517856420597961


invite_cache = {}

# === MESSAGE AUTO VOTE ===

async def vote_reminder():
    await bot.wait_until_ready()
    channel = bot.get_channel(VOTE_CHANNEL_ID)
    if not channel:
        print("❌ Salon de vote introuvable.")
        return

    while not bot.is_closed():
        try:
            embed = discord.Embed(
                title="🗳️ Vote pour Isolya FA V1 !",
                description="**Vote toutes les 2 heures pour nous soutenir !**\n👉 [Vote ici](https://top-serveurs.net/gta/isolyafa)",
                color=0x00ff00
            )
            embed.set_footer(text="Merci de ton soutien ❤️")
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Erreur dans le rappel de vote : {e}")
        await asyncio.sleep(2 * 60 * 60)  # 2 heures

# === BOT EVENTS ===
@bot.event
async def on_ready():

    # === Actualiser les invitations pour tous les serveurs ===
    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = await guild.invites()
        except:
            invite_cache[guild.id] = []


    # === Message de statut ===
    channel = bot.get_channel(1400837582752845865)
    if channel:
        await channel.send("✅ Le bot est de nouveau en ligne !")

    print(f"[✅ BOT EN LIGNE] Connecté en tant que {bot.user}")


@bot.event
async def on_member_join(member):
    guild = member.guild
    channel = bot.get_channel(1399517854675501112)  # Ton salon de bienvenue

    # === Message de bienvenue classique ===
    embed = discord.Embed(
        title=f"👋 Bienvenue {member.display_name} !",
        description="📜 Lis bien le règlement et régale-toi en jeu 🎮",
        color=0x3498db
    )
    embed.set_footer(text="Bienvenue sur Isolya FA V1")
    if channel:
        await channel.send(embed=embed)

    # === Système de suivi d’invitations ===
    try:
        invites_before = invite_cache.get(guild.id, [])
        invites_after = await guild.invites()

        used_invite = None
        for invite in invites_before:
            for new_invite in invites_after:
                if invite.code == new_invite.code and invite.uses < new_invite.uses:
                    used_invite = new_invite
                    break

        invite_cache[guild.id] = invites_after  # Met à jour le cache

        if used_invite and used_invite.inviter:
            inviter = used_invite.inviter

            # Ajoute l'invitation en base PostgreSQL
            add_invitation(inviter.id)
            count = get_invitation_count(inviter.id)

            if channel:
                await channel.send(
                    f"🧭 {member.mention} a été invité par **{inviter.name}**.\n"
                    f"🎉 {inviter.name} a maintenant **{count} invitation(s)** !"
                )
        else:
            if channel:
                await channel.send(f"ℹ️ {member.mention} a rejoint, mais je ne sais pas avec quelle invitation.")

    except Exception as e:
        print(f"[❌ ERREUR on_member_join] {e}")



# === COMMANDE REBOOT ===
@bot.command()
@commands.is_owner()
async def reboot(ctx):
    await ctx.send("🔄 Le bot redémarre...")
    await bot.close()
    subprocess.call([sys.executable, __file__])

# === COMMANDE BONJOUR ===
@bot.command()
async def bonjour(ctx):
    await ctx.send(f"Bonjour {ctx.author} !")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong !")

@bot.command()
async def pileouface(ctx):
    await ctx.send(random.choice(["Pile", "Face"]))

@bot.command()
async def roll(ctx):
    await ctx.send(random.randint(1, 6))

# === VERIFICATION BUTTON ===
class VerifButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Accepter le règlement", style=discord.ButtonStyle.success, custom_id="verif_button")
    async def verif(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(CITOYEN_ROLE_ID)
        if not role:
            return await interaction.response.send_message("❌ Rôle introuvable. Merci de contacter un admin.", ephemeral=True)
        if role in interaction.user.roles:
            return await interaction.response.send_message("✅ Tu as déjà le rôle Citoyen.", ephemeral=True)
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Le rôle est au-dessus du bot. Corrige les permissions.", ephemeral=True)
        try:
            await interaction.user.add_roles(role, reason="Acceptation du règlement")
            await interaction.response.send_message("🎉 Tu as accepté le règlement !", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Permission refusée. Contacte un admin.", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def setupverif(ctx):
    if ctx.channel.id != VERIF_CHANNEL_ID:
        return await ctx.send("❌ Cette commande doit être utilisée dans le salon de vérification.")

    reglement = (
        "**RÈGLEMENT DU DISCORD — Isolya FA V1**\n"
        "Bienvenue sur le Discord officiel de **Isolya FA V1**.\n"
        "Merci de lire attentivement ce règlement avant toute participation.\n\n"
        "**1. Respect & Comportement**\n"
        "Aucune insulte, discrimination, harcèlement ou propos haineux.\n\n"
        "**2. Utilisation des canaux**\n"
        "Respecte les canaux et ne spamme pas.\n\n"
        "**3. Noms & avatars**\n"
        "Pseudos et avatars corrects obligatoires.\n\n"
        "**4. Publicité & Spam**\n"
        "Interdits sans autorisation.\n\n"
        "**5. Contenu interdit**\n"
        "Pas de contenu NSFW, illégal, ou choquant.\n\n"
        "**6. Règlement du serveur FiveM**\n"
        "RP uniquement en jeu. Règlement IG à respecter.\n\n"
        "**7. Sanctions**\n"
        "Le staff peut sanctionner sans préavis.\n\n"
        "*En rejoignant le serveur, tu acceptes ce règlement.*"
    )

    embed = discord.Embed(
        title="📜 Règlement Discord - Isolya FA V1",
        description=reglement,
        color=0xf1c40f
    )
    embed.set_footer(text="Clique sur le bouton ci-dessous pour accepter le règlement")
    await ctx.send(embed=embed, view=VerifButton())

# === WARN STAFF  ===

@bot.command()
async def warn(ctx, member: discord.Member = None, *, reason: str = None):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    warn_role = ctx.guild.get_role(WARN_ROLE_ID)

    if staff_role not in ctx.author.roles:
        return await ctx.send("❌ Tu n'as pas la permission d'utiliser cette commande.")

    if member is None or reason is None:
        return await ctx.send("❗ Utilisation : !warn @utilisateur raison")

    # Ajoute le rôle warn
    if warn_role:
        if warn_role not in member.roles:
            try:
                warns_via_bot.add(member.id)  # ← on ajoute l'ID ici !
                await member.add_roles(warn_role, reason="Avertissement (warn)")
            except discord.Forbidden:
                return await ctx.send("❌ Je n'ai pas la permission d'ajouter le rôle à ce membre.")
        else:
            await ctx.send("⚠️ L'utilisateur a déjà le rôle warn.")
    else:
        await ctx.send("❌ Le rôle warn est introuvable.")

    # Envoie un MP à l'utilisateur
    try:
        await member.send(f"⚠️ Tu as été averti sur **{ctx.guild.name}** pour la raison : {reason}.")
    except:
        pass  # Si l'utilisateur a ses DM fermés

    # Log dans le salon
    log_channel = ctx.guild.get_channel(WARN_LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="🚨 Avertissement (Warn)",
            description=f"**Membre :** {member.mention}\n**Par :** {ctx.author.mention}\n**Raison :** {reason}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        await log_channel.send(embed=embed)

    await ctx.send(f"✅ {member.mention} a été averti et a reçu le rôle warn.")

# Retire le rôle warn

@bot.command()
async def unwarn(ctx, member: discord.Member = None):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    warn_role = ctx.guild.get_role(WARN_ROLE_ID)

    if staff_role not in ctx.author.roles:
        return await ctx.send("❌ Tu n'as pas la permission d'utiliser cette commande.")

    if member is None:
        return await ctx.send("❗ Utilisation : !unwarn @utilisateur")

    if warn_role not in member.roles:
        return await ctx.send("ℹ️ Cet utilisateur n’a pas le rôle warn.")

    try:
        await member.remove_roles(warn_role, reason="Retrait de l'avertissement")
        await ctx.send(f"✅ Le rôle warn a été retiré de {member.mention}.")
    except discord.Forbidden:
        await ctx.send("❌ Je n’ai pas les permissions pour retirer ce rôle.")

    # Log dans le salon
    log_channel = ctx.guild.get_channel(WARN_LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="✅ Avertissement retiré (Unwarn)",
            description=f"**Membre :** {member.mention}\n**Par :** {ctx.author.mention}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        await log_channel.send(embed=embed)

# === WARN A LA MAIN ===

@bot.event
async def on_member_update(before, after):
    warn_role = after.guild.get_role(WARN_ROLE_ID)
    log_channel = after.guild.get_channel(WARN_LOG_CHANNEL_ID)

    if not warn_role or not log_channel:
        return

    await asyncio.sleep(4)  # Attend que les logs soient bien enregistrés

    # === Rôle WARN ajouté ===
    if warn_role not in before.roles and warn_role in after.roles:
        # On ignore le log si c'est le bot qui a warn (commande)
        if after.id in warns_via_bot:
            warns_via_bot.remove(after.id)
            return

        added_by = "❓ Inconnu (non trouvé dans les logs)"
        async for entry in after.guild.audit_logs(limit=10, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id and warn_role in entry.changes.after:
                added_by = entry.user.mention
                break

        embed = discord.Embed(
            title="⚠️ Rôle WARN ajouté à la main",
            description=(
                f"**Membre warn :** {after.mention}\n"
                f"**Ajouté par :** {added_by}"
            ),
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        await log_channel.send(embed=embed)

    # === Rôle WARN retiré ===
    elif warn_role in before.roles and warn_role not in after.roles:
        removed_by = "❓ Inconnu (non trouvé dans les logs)"
        async for entry in after.guild.audit_logs(limit=10, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id and warn_role in entry.changes.before:
                removed_by = entry.user.mention
                break

        embed = discord.Embed(
            title="✅ Rôle WARN retiré à la main",
            description=(
                f"**Membre :** {after.mention}\n"
                f"**Retiré par :** {removed_by}"
            ),
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        await log_channel.send(embed=embed)

# === !invites ===

@bot.command()
async def invites(ctx, member: discord.Member = None):
    """Affiche le nombre d'invitations d'un membre."""
    member = member or ctx.author
    count = get_invitation_count(member.id)
    await ctx.send(f"🔗 {member.mention} a actuellement **{count} invitation(s)** .")


@bot.command()
async def topinvites(ctx):
    """Classement des meilleurs inviteurs (base PostgreSQL)"""
    top = get_top_inviters(10)
    msg = "**Top Inviteurs :**\n"
    for i, (user_id, invite_count) in enumerate(top, 1):
        member = ctx.guild.get_member(int(user_id))
        name = member.display_name if member else f"User {user_id}"
        msg += f"{i}. {name} — {invite_count} invitations\n"
    await ctx.send(msg)



# === FERMETURE DE TICKET AVEC TRANSCRIPTION ===
class CloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_channel = interaction.channel
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

        messages = [msg async for msg in ticket_channel.history(limit=100)]
        messages.reverse()

        lines = [f"Ticket : {ticket_channel.name}", f"Fermé par : {interaction.user}", f"Date : {datetime.utcnow()} UTC", "\n--- Messages ---\n"]
        for msg in messages:
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            author = f"{msg.author} (ID: {msg.author.id})"
            content = msg.content.strip()
            if content:
                lines.append(f"[{timestamp}] {author} : {content}")

        transcript = "\n".join(lines)
        file = discord.File(io.StringIO(transcript), filename=f"{ticket_channel.name}.txt")

        if log_channel:
            await log_channel.send(
                content=f"📤 Ticket fermé : `{ticket_channel.name}` par {interaction.user.mention}",
                file=file
            )

        await interaction.response.send_message("⏳ Ticket fermé dans 5 secondes...", ephemeral=True)
        await asyncio.sleep(5)
        await ticket_channel.delete()

# === MENU POUR CRÉER UN TICKET ===
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ticket Illégal", value="illégal", description="➡️ Problème ou demande illégal"),
            discord.SelectOption(label="Ticket Legal", value="legal", description="➡️ Problème ou demande légal"),
            discord.SelectOption(label="Ticket Remboursement", value="remboursement", description="➡️ Demande de remboursement"),
            discord.SelectOption(label="Ticket Candidature", value="candidature", description="➡️ Postuler au staff"),
            discord.SelectOption(label="Ticket Wipe", value="wipe", description="➡️ Demande ou litige concernant un Wipe"),
            discord.SelectOption(label="Ticket MortRP", value="mortrp", description="➡️ Demande de MortRP"),
            discord.SelectOption(label="Ticket Dévelopement", value="dévelopement", description="➡️ Demande concernant le dév"),
            discord.SelectOption(label="Ticket ScèneRP", value="scènerp", description="➡️ Demande de modération d'une scène ou autre"),
        ]
        super().__init__(custom_id="ticket_select", placeholder="📩 Choisis une catégorie de ticket", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category_id = CATEGORY_IDS.get(self.values[0])
        category = interaction.guild.get_channel(category_id)
        user = interaction.user
        channel_name = f"{self.values[0]}-{user.name.lower()}"

        # Vérifie si l’utilisateur a déjà un ticket
        for channel in interaction.guild.text_channels:
            if channel.name == channel_name:
                return await interaction.response.send_message("❗ Tu as déjà un ticket ouvert.", ephemeral=True)

        # Ajout du rôle staff aux permissions
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        if category is None:
            return await interaction.response.send_message("❌ Catégorie introuvable. Préviens un admin.", ephemeral=True)

        # Création du ticket
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            topic=f"Ticket {self.values[0]} de {user.name}"
        )

        await ticket_channel.send(
            f"🎫 Ticket ouvert par {user.mention}\n🔒 Clique sur le bouton ci-dessous pour fermer le ticket.",
            view=CloseButton()
        )

        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"📥 Ticket `{self.values[0]}` ouvert par {user.mention} → {ticket_channel.mention}")

        await interaction.response.send_message(f"✅ Ticket créé ici : {ticket_channel.mention}", ephemeral=True)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.command()
async def setticket(ctx):
    await ctx.send("# 📬 Sélectionne une catégorie de ticket :", view=TicketView())

# === GIVEAWAYS ===
@bot.command()
@commands.has_permissions(manage_guild=True)
async def giveaway(ctx, duration: str, *, prize: str):
    import re

    time_regex = re.match(r"^(\d+)([smhd])$", duration)
    if not time_regex:
        return await ctx.send("❌ Format invalide. Utilise `10s`, `5m`, `1h`, `1d`.")

    time_value, time_unit = int(time_regex[1]), time_regex[2]
    seconds = {"s": 1, "m": 60, "h": 3600, "d": 86400}[time_unit]
    total_seconds = time_value * seconds

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prix :** {prize}\nRéagis avec 🎉 pour participer !\nDurée : {duration}",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Lancé par {ctx.author}", icon_url=ctx.author.display_avatar.url)
    giveaway_msg = await ctx.send(embed=embed)
    await giveaway_msg.add_reaction("🎉")

    await asyncio.sleep(total_seconds)

    message = await ctx.channel.fetch_message(giveaway_msg.id)
    users = [user async for user in message.reactions[0].users()]
    users = [user for user in users if not user.bot]

    if not users:
        return await ctx.send("❌ Personne n’a participé.")

    winner = random.choice(users)
    result_text = f"🎊 Félicitations {winner.mention}, tu as gagné **{prize}** !"

    # Envoie dans le salon où la commande a été tapée
    await ctx.send(result_text)

    # Envoie dans le salon Log Giveaways
    log_channel = ctx.guild.get_channel(LOG_GIVEAWAY_CHANNEL_ID)
    if log_channel:
        await log_channel.send(result_text)


# === LANCEMENT FINAL ===
token = os.environ.get("TOKEN_BOT_DISCORD")
if not token:
    print("[❌ ERREUR] La variable d'environnement TOKEN_BOT_DISCORD est manquante.")
else:
    bot.run(token)
