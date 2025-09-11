import time
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import List, Dict, Any, Optional
from utils.data import load_json, save_json
from cogs.hub import refresh_hub

MAILBOX_FILE = "mailbox.json"


async def render_mailbox(self, user_id: int):
    mail_cog = self.bot.get_cog("Mailbox")
    embed = discord.Embed(title="📬 Mailbox", color=discord.Color.blurple())

    if not mail_cog:
        embed.description = "⚠️ Mailbox system unavailable."
        return embed

    inbox = mail_cog.get_inbox(user_id)
    unread_count = len([m for m in inbox if not m["read"]])

    embed.description = f"📨 You have **{len(inbox)}** messages ({unread_count} unread)."
    embed.set_footer(text="Use the buttons below to send or view messages.")
    return embed

async def render_registry(self, user_id: int):
    embed = discord.Embed(
        title="📜 Guild Recipe Registry",
        description="Search recipes to see who can craft them.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Use the button below to search the registry.")
    return embed

async def render_trades(self, user_id: int):
    embed = discord.Embed(
        title="📦 Trade Board",
        description="Post items for sale, request items, or make trade offers.\n\nComing soon…",
        color=discord.Color.orange()
    )
    return embed




def now_ts() -> int:
    return int(time.time())

class Mail(commands.Cog):
    """In-bot mailbox for craft/trade requests and messages."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store: Dict[str, List[Dict[str, Any]]] = load_json(MAILBOX_FILE, {})  # { user_id: [msg, ...] }

    def _save(self):
        save_json(MAILBOX_FILE, self.store)

    # ------------- Public API -------------
    def send_mail(self, to_user_id: int, from_user_id: int, subject: str, body: str) -> Dict[str, Any]:
        msg = {
            "id": f"m{now_ts()}_{from_user_id}",
            "from": str(from_user_id),
            "to": str(to_user_id),
            "subject": subject[:120],
            "body": body[:1800],
            "ts": now_ts(),
            "read": False,
        }
        self.store.setdefault(str(to_user_id), []).append(msg)
        self._save()
        return msg

    def get_inbox(self, user_id: int) -> List[Dict[str, Any]]:
        return sorted(self.store.get(str(user_id), []), key=lambda m: m["ts"], reverse=True)

    def mark_read(self, user_id: int, msg_id: str):
        inbox = self.store.get(str(user_id), [])
        for m in inbox:
            if m["id"] == msg_id:
                m["read"] = True
                self._save()
                break

    # ------------- UI: Buttons -------------
    def build_mail_buttons(self, user_id: int):
        v = View(timeout=180)
        v.add_item(Button(label="📥 Inbox", style=discord.ButtonStyle.primary, custom_id=f"mail_inbox_{user_id}"))
        v.add_item(Button(label="✉️ Compose", style=discord.ButtonStyle.success, custom_id=f"mail_compose_{user_id}"))
        return v

    # ------------- UI: Modals -------------
    class ComposeModal(Modal, title="✉️ Compose Mail"):
        def __init__(self, cog: "Mail", from_user_id: int, to_user_id: Optional[int] = None, subject_prefill: str = "", body_prefill: str = ""):
            super().__init__(timeout=240)
            self.cog = cog
            self.from_user_id = from_user_id
            self.to_user_id = to_user_id

            self.to = TextInput(label="To (User ID)", required=(to_user_id is None), placeholder="e.g. 123456789012345678")
            self.subject = TextInput(label="Subject", required=True, default=subject_prefill[:120])
            self.body = TextInput(label="Message", required=True, style=discord.TextStyle.paragraph, default=body_prefill[:1800])

            if to_user_id is None:
                self.add_item(self.to)
            self.add_item(self.subject)
            self.add_item(self.body)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                to_id = int(self.to.value) if self.to_user_id is None else int(self.to_user_id)
            except Exception:
                return await interaction.response.send_message("⚠️ Invalid target user ID.", ephemeral=True)

            self.cog.send_mail(
                to_user_id=to_id,
                from_user_id=interaction.user.id,
                subject=self.subject.value,
                body=self.body.value
            )
            await refresh_hub(interaction, section="mailbox")

    # ------------- UI: Views -------------
    class InboxView(View):
        def __init__(self, cog: "Mail", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id

            inbox = self.cog.get_inbox(user_id)
            if not inbox:
                self.add_item(Button(label="Inbox is empty", style=discord.ButtonStyle.secondary, disabled=True))
                return

            for m in inbox[:25]:
                label = f"{'✅' if m['read'] else '🆕'} {m['subject']} — from {m['from']}"
                self.add_item(self._OpenBtn(self.cog, self.user_id, m["id"], label[:80]))

        class _OpenBtn(Button):
            def __init__(self, cog: "Mail", user_id: int, msg_id: str, label: str):
                super().__init__(label=label, style=discord.ButtonStyle.secondary)
                self.cog = cog
                self.user_id = user_id
                self.msg_id = msg_id

            async def callback(self, interaction: discord.Interaction):
                inbox = self.cog.get_inbox(self.user_id)
                msg = next((m for m in inbox if m["id"] == self.msg_id), None)
                if not msg:
                    return await interaction.response.send_message("⚠️ Message not found.", ephemeral=True)

                self.cog.mark_read(self.user_id, self.msg_id)
                from_member = interaction.guild.get_member(int(msg["from"])) if interaction.guild else None
                from_name = from_member.display_name if from_member else msg["from"]

                e = discord.Embed(
                    title=f"✉️ {msg['subject']}",
                    description=msg["body"],
                    color=discord.Color.blurple()
                )
                e.add_field(name="From", value=from_name)
                e.set_footer(text=f"ID: {msg['id']}")

                # Reply button
                v = View(timeout=180)
                v.add_item(self._ReplyBtn(self.cog, self.user_id, int(msg["from"]), f"RE: {msg['subject']}"))
                await interaction.response.edit_message(embed=e, view=v)

        class _ReplyBtn(Button):
            def __init__(self, cog: "Mail", user_id: int, to_user_id: int, subject: str):
                super().__init__(label="↩️ Reply", style=discord.ButtonStyle.primary)
                self.cog = cog
                self.user_id = user_id
                self.to_user_id = to_user_id
                self.subject = subject

            async def callback(self, interaction: discord.Interaction):
                modal = Mail.ComposeModal(self.cog, from_user_id=self.user_id, to_user_id=self.to_user_id, subject_prefill=self.subject)
                await interaction.response.send_modal(modal)

    # ------------- Component IDs -------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type or not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")  # type: ignore[attr-defined]
        if not cid or not isinstance(cid, str):
            return

        uid = interaction.user.id
        if cid == f"mail_inbox_{uid}":
            embed = discord.Embed(title="📥 Inbox", description="Your in-bot messages.", color=discord.Color.blurple())
            view = Mail.InboxView(self, uid)
            return await interaction.response.edit_message(embed=embed, view=view)

        if cid == f"mail_compose_{uid}":
            modal = Mail.ComposeModal(self, from_user_id=uid)
            return await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot):
    await bot.add_cog(Mail(bot))

