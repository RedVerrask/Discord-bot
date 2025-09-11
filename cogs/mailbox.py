import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from typing import Dict, List, Any
from utils.data import load_json, save_json
from cogs.hub import refresh_hub

MAILBOX_FILE = "data/mailbox.json"

class Mailbox(commands.Cog):
    """Guild-wide in-bot messaging system with unread tracking + badges."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # { user_id: [ {from, subject, body, read} ] }
        self.mail: Dict[str, List[Dict[str, Any]]] = load_json(MAILBOX_FILE, {})

    def save(self):
        save_json(MAILBOX_FILE, self.mail)

    # ==================================================
    # Public API
    # ==================================================
    def get_inbox(self, user_id: int):
        return self.mail.get(str(user_id), [])

    def get_unread_count(self, user_id: int) -> int:
        """Return number of unread messages for a user."""
        return sum(1 for msg in self.mail.get(str(user_id), []) if not msg.get("read", False))

    def send_message(self, from_id: int, to_id: int, subject: str, body: str):
        """Add a new message to someone's inbox + auto-refresh hub."""
        entry = {
            "from": from_id,
            "subject": subject or "(No Subject)",
            "body": body,
            "read": False,
        }
        self.mail.setdefault(str(to_id), []).append(entry)
        self.save()

        # 🔔 Auto-refresh hub for recipient
        guild_user = self.bot.get_user(to_id)
        if guild_user:
            try:
                dummy_interaction = discord.Object(id=to_id)
                dummy_interaction.user = guild_user
                self.bot.loop.create_task(refresh_hub(dummy_interaction, section="mailbox"))
            except Exception:
                pass

        return entry

    def mark_read(self, user_id: int, index: int, read: bool = True):
        inbox = self.mail.get(str(user_id), [])
        if 0 <= index < len(inbox):
            inbox[index]["read"] = read
            self.save()

    def delete_message(self, user_id: int, index: int):
        inbox = self.mail.get(str(user_id), [])
        if 0 <= index < len(inbox):
            inbox.pop(index)
            self.save()

    # ==================================================
    # UI — Modals
    # ==================================================
    class ComposeModal(Modal, title="📨 Compose Message"):
        def __init__(self, cog: "Mailbox", from_user_id: int, to_user_id: int, subject_prefill: str = "", body_prefill: str = ""):
            super().__init__(timeout=300)
            self.cog = cog
            self.from_user_id = from_user_id
            self.to_user_id = to_user_id

            self.subject = TextInput(label="Subject", placeholder="e.g. Trade Inquiry", required=False, default=subject_prefill)
            self.body = TextInput(label="Message", style=discord.TextStyle.long, placeholder="Write your message here", required=True, default=body_prefill)
            self.add_item(self.subject)
            self.add_item(self.body)

        async def on_submit(self, interaction: discord.Interaction):
            self.cog.send_message(
                from_id=self.from_user_id,
                to_id=self.to_user_id,
                subject=self.subject.value,
                body=self.body.value,
            )
            await refresh_hub(interaction, section="mailbox")

    # ==================================================
    # UI — Views
    # ==================================================
    class InboxView(View):
        def __init__(self, cog: "Mailbox", user_id: int):
            super().__init__(timeout=300)
            self.cog = cog
            self.user_id = user_id

            inbox = self.cog.get_inbox(user_id)
            if not inbox:
                self.add_item(Button(label="Inbox Empty", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                for idx, msg in enumerate(inbox[:5]):  # Show up to 5 messages
                    label = f"{'📩' if not msg['read'] else '📨'} {msg['subject']}"
                    self.add_item(self._MsgBtn(self.cog, user_id, idx, label))

        class _MsgBtn(Button):
            def __init__(self, cog: "Mailbox", user_id: int, index: int, label: str):
                super().__init__(label=label[:80], style=discord.ButtonStyle.primary)
                self.cog = cog
                self.user_id = user_id
                self.index = index

            async def callback(self, interaction: discord.Interaction):
                inbox = self.cog.get_inbox(self.user_id)
                if self.index >= len(inbox):
                    return await interaction.response.send_message("⚠️ This message no longer exists.", ephemeral=True)

                msg = inbox[self.index]
                self.cog.mark_read(self.user_id, self.index)

                sender = interaction.client.get_user(msg["from"])
                sender_name = sender.display_name if sender else str(msg["from"])

                e = discord.Embed(
                    title=f"✉️ {msg['subject']}",
                    description=f"**From:** {sender_name}\n\n{msg['body']}",
                    color=discord.Color.blurple(),
                )
                v = Mailbox.MessageActions(self.cog, self.user_id, self.index)
                await interaction.response.edit_message(embed=e, view=v)
                await refresh_hub(interaction, section="mailbox")

    class MessageActions(View):
        def __init__(self, cog: "Mailbox", user_id: int, index: int):
            super().__init__(timeout=180)
            self.cog = cog
            self.user_id = user_id
            self.index = index
            self.add_item(self._ReplyBtn(self.cog, self.user_id, self.index))
            self.add_item(self._DeleteBtn(self.cog, self.user_id, self.index))
            self.add_item(self._BackBtn(self.cog, self.user_id))

        class _ReplyBtn(Button):
            def __init__(self, cog: "Mailbox", user_id: int, index: int):
                super().__init__(label="↩️ Reply", style=discord.ButtonStyle.success)
                self.cog = cog
                self.user_id = user_id
                self.index = index

            async def callback(self, interaction: discord.Interaction):
                inbox = self.cog.get_inbox(self.user_id)
                msg = inbox[self.index]
                modal = Mailbox.ComposeModal(self.cog, from_user_id=self.user_id, to_user_id=msg["from"], subject_prefill=f"Re: {msg['subject']}")
                await interaction.response.send_modal(modal)

        class _DeleteBtn(Button):
            def __init__(self, cog: "Mailbox", user_id: int, index: int):
                super().__init__(label="🗑 Delete", style=discord.ButtonStyle.danger)
                self.cog = cog
                self.user_id = user_id
                self.index = index

            async def callback(self, interaction: discord.Interaction):
                self.cog.delete_message(self.user_id, self.index)
                await refresh_hub(interaction, section="mailbox")

        class _BackBtn(Button):
            def __init__(self, cog: "Mailbox", user_id: int):
                super().__init__(label="⬅ Back", style=discord.ButtonStyle.secondary)
                self.cog = cog
                self.user_id = user_id

            async def callback(self, interaction: discord.Interaction):
                e = discord.Embed(title="📬 Inbox", description="Select a message to view.", color=discord.Color.blurple())
                v = Mailbox.InboxView(self.cog, self.user_id)
                await interaction.response.edit_message(embed=e, view=v)

    # ==================================================
    # Hub Buttons
    # ==================================================
    def build_mailbox_buttons(self, user_id: int):
        v = View(timeout=180)
        unread_count = self.get_unread_count(user_id)
        inbox_label = f"📬 Inbox ({unread_count} Unread)" if unread_count > 0 else "📬 Inbox"
        v.add_item(Button(label="📨 Compose", style=discord.ButtonStyle.success, custom_id=f"mb_compose_{user_id}"))
        v.add_item(Button(label=inbox_label, style=discord.ButtonStyle.primary, custom_id=f"mb_inbox_{user_id}"))
        return v

    # ==================================================
    # Interaction Handling
    # ==================================================
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type or not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")
        if not cid or not isinstance(cid, str):
            return

        uid = interaction.user.id

        # Compose new message
        if cid == f"mb_compose_{uid}":
            modal = Mailbox.ComposeModal(self, from_user_id=uid, to_user_id=uid)
            return await interaction.response.send_modal(modal)

        # View inbox
        if cid == f"mb_inbox_{uid}":
            inbox = self.get_inbox(uid)
            unread = self.get_unread_count(uid)
            e = discord.Embed(
                title="📬 Inbox",
                description=f"You have **{len(inbox)}** total messages.\n**{unread} unread**.",
                color=discord.Color.blurple()
            )
            v = Mailbox.InboxView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)


async def setup(bot: commands.Bot):
    await bot.add_cog(Mailbox(bot))
