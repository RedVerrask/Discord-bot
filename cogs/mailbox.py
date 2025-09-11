# cogs/mailbox.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from utils.data import load_json, save_json
from cogs.hub import refresh_hub

MAILBOX_FILE = "data/mailbox.json"


class Mailbox(commands.Cog):
    """Guild-wide in-bot messaging system."""

    def __init__(self, bot):
        self.bot = bot
        self.mail = load_json(MAILBOX_FILE, {})  # { user_id: [ {from, subject, body, read} ] }

    def save(self):
        save_json(MAILBOX_FILE, self.mail)

    # ---------------- Public API ----------------
    def get_inbox(self, user_id: int):
        return self.mail.get(str(user_id), [])

    def send_message(self, from_id: int, to_id: int, subject: str, body: str):
        entry = {
            "from": from_id,
            "subject": subject or "(No Subject)",
            "body": body,
            "read": False,
        }
        self.mail.setdefault(str(to_id), []).append(entry)
        self.save()
        return entry

    def delete_message(self, user_id: int, index: int):
        inbox = self.mail.get(str(user_id), [])
        if 0 <= index < len(inbox):
            inbox.pop(index)
            self.save()

    def mark_read(self, user_id: int, index: int, read: bool = True):
        inbox = self.mail.get(str(user_id), [])
        if 0 <= index < len(inbox):
            inbox[index]["read"] = read
            self.save()

    # ---------------- UI ----------------
    class ComposeModal(Modal, title="📨 Compose Message"):
        def __init__(self, cog, from_user_id: int, to_user_id: int, subject_prefill: str = "", body_prefill: str = ""):
            super().__init__(timeout=300)
            self.cog, self.from_user_id, self.to_user_id = cog, from_user_id, to_user_id
            self.subject = TextInput(label="Subject", required=False, default=subject_prefill)
            self.body = TextInput(label="Body", style=discord.TextStyle.long, required=True, default=body_prefill)
            self.add_item(self.subject)
            self.add_item(self.body)

        async def on_submit(self, interaction: discord.Interaction):
            self.cog.send_message(self.from_user_id, self.to_user_id, self.subject.value, self.body.value)
            await refresh_hub(interaction, "mailbox")

    class InboxView(View):
        def __init__(self, cog, user_id: int):
            super().__init__(timeout=300)
            inbox = cog.get_inbox(user_id)
            if not inbox:
                self.add_item(Button(label="Inbox Empty", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                for idx, msg in enumerate(inbox[:5]):  # show up to 5
                    label = f"{'📩' if not msg['read'] else '📨'} {msg['subject']}"
                    self.add_item(Mailbox._MsgBtn(cog, user_id, idx, label))

        class _MsgBtn(Button):
            def __init__(self, cog, user_id: int, index: int, label: str):
                super().__init__(label=label, style=discord.ButtonStyle.primary)
                self.cog, self.user_id, self.index = cog, user_id, index

            async def callback(self, interaction: discord.Interaction):
                msg = self.cog.get_inbox(self.user_id)[self.index]
                self.cog.mark_read(self.user_id, self.index, True)
                sender = interaction.guild.get_member(msg["from"]) if interaction.guild else None
                sender_name = sender.display_name if sender else str(msg["from"])

                e = discord.Embed(
                    title=f"📨 {msg['subject']}",
                    description=msg["body"],
                    color=discord.Color.blurple()
                )
                e.set_footer(text=f"From: {sender_name}")
                v = Mailbox.MessageActions(self.cog, self.user_id, self.index)
                await interaction.response.edit_message(embed=e, view=v)

    class MessageActions(View):
        def __init__(self, cog, user_id: int, index: int):
            super().__init__(timeout=180)
            self.add_item(Mailbox._ReplyBtn(cog, user_id, index))
            self.add_item(Mailbox._DeleteBtn(cog, user_id, index))
            self.add_item(Mailbox._BackBtn(cog, user_id))

        class _ReplyBtn(Button):
            def __init__(self, cog, user_id: int, index: int):
                super().__init__(label="↩️ Reply", style=discord.ButtonStyle.success)
                self.cog, self.user_id, self.index = cog, user_id, index

            async def callback(self, interaction: discord.Interaction):
                msg = self.cog.get_inbox(self.user_id)[self.index]
                modal = Mailbox.ComposeModal(self.cog, self.user_id, msg["from"], subject_prefill=f"Re: {msg['subject']}")
                await interaction.response.send_modal(modal)

        class _DeleteBtn(Button):
            def __init__(self, cog, user_id: int, index: int):
                super().__init__(label="🗑 Delete", style=discord.ButtonStyle.danger)
                self.cog, self.user_id, self.index = cog, user_id, index

            async def callback(self, interaction: discord.Interaction):
                self.cog.delete_message(self.user_id, self.index)
                await refresh_hub(interaction, "mailbox")

        class _BackBtn(Button):
            def __init__(self, cog, user_id: int):
                super().__init__(label="⬅ Back", style=discord.ButtonStyle.secondary)
                self.cog, self.user_id = cog, user_id

            async def callback(self, interaction: discord.Interaction):
                e = discord.Embed(title="📬 Inbox", description="Select a message to view.", color=discord.Color.blurple())
                v = Mailbox.InboxView(self.cog, self.user_id)
                await interaction.response.edit_message(embed=e, view=v)

    # ---------------- Hub ----------------
    def build_mailbox_buttons(self, user_id: int):
        v = View(timeout=180)
        v.add_item(Button(label="📨 Compose", style=discord.ButtonStyle.success, custom_id=f"mb_compose_{user_id}"))
        v.add_item(Button(label="📬 Inbox", style=discord.ButtonStyle.primary, custom_id=f"mb_inbox_{user_id}"))
        return v

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        cid = interaction.data.get("custom_id") if getattr(interaction, "data", None) else None
        if not cid: 
            return
        uid = interaction.user.id

        if cid == f"mb_compose_{uid}":
            modal = Mailbox.ComposeModal(self, uid, uid)
            return await interaction.response.send_modal(modal)

        if cid == f"mb_inbox_{uid}":
            e = discord.Embed(title="📬 Inbox", description="Select a message to view.", color=discord.Color.blurple())
            v = Mailbox.InboxView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)


async def setup(bot):
    await bot.add_cog(Mailbox(bot))
