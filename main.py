import discord
import os
import aiohttp

# ─── CONFIGURACIÓN DESDE VARIABLES DE ENTORNO ───────────────────────────────
# En Railway, estas variables se configuran en el panel (nunca en el código)
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = int(os.environ.get("GUILD_ID", "1020792950235607141"))
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "IamGustav-Student/GymSaaS")

# IDs de Canales
RULES_CH_ID = int(os.environ.get("RULES_CH_ID", "1100924879441772585"))
ROLES_CH_ID = int(os.environ.get("ROLES_CH_ID", "1084543390126968953"))
SHOWCASE_CH_ID = int(os.environ.get("SHOWCASE_CH_ID", "1504573704225554552"))

class MasterBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.role_map = {
            "💻": "〔 💻 〕FullStack",
            "🎮": "〔 🎮 〕Pro Gamer",
            "🔔": "〔 🔔 〕Notificaciones"
        }
        # Cargar repositorio persistente o usar el valor por defecto
        self.config_path = "active_repo.txt"
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.github_repo = f.read().strip()
            except Exception:
                self.github_repo = os.environ.get("GITHUB_REPO", "IamGustav-Student/GymSaaS")
        else:
            self.github_repo = os.environ.get("GITHUB_REPO", "IamGustav-Student/GymSaaS")

    async def on_ready(self):
        print(f"[OK] Master Bot activo como {self.user}")
        print(f"[OK] Conectado al servidor ID: {GUILD_ID}")

    # ─── BIENVENIDA AUTOMÁTICA ───────────────────────────────────────────────
    async def on_member_join(self, member):
        guild = member.guild
        welcome_channel = discord.utils.get(guild.text_channels, name="welcome-center")
        if not welcome_channel: return

        embed = discord.Embed(
            title=f"〢─── ⚡ // NUEVO OPERATIVO DETECTADO ───〢",
            description=f"**{member.mention}** ha ingresado al sistema.\nBienvenido a **La Guardia**.",
            color=discord.Color.from_str("#03DAC6")
        )
        embed.add_field(name="[ PASO 1 ]", value="📋 Leé las reglas en <#" + str(RULES_CH_ID) + ">", inline=False)
        embed.add_field(name="[ PASO 2 ]", value="🎭 Elegí tus roles en <#" + str(ROLES_CH_ID) + ">", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Usuario #{guild.member_count}")
        await welcome_channel.send(embed=embed)

    # ─── COMANDOS Y AUTOMATIZACIONES ────────────────────────────────────────
    async def on_message(self, message):
        if message.author == self.user: return

        # Comando !tarea [título] | [descripción]
        if message.content.startswith("!tarea"):
            content = message.content[7:].strip()
            if not content:
                await message.channel.send("❌ Uso: `!tarea Título | Descripción (opcional)`")
                return
            parts = content.split("|")
            title = parts[0].strip()
            body = parts[1].strip() if len(parts) > 1 else f"Creada desde Discord por {message.author}"

            async with aiohttp.ClientSession() as session:
                url = f"https://api.github.com/repos/{self.github_repo}/issues"
                headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
                async with session.post(url, headers=headers, json={"title": title, "body": body}) as resp:
                    if resp.status == 201:
                        data = await resp.json()
                        embed = discord.Embed(
                            title="✅ Tarea Creada en GitHub",
                            description=f"Issue **#{data['number']}** creada con éxito.",
                            url=data["html_url"],
                            color=discord.Color.green()
                        )
                        embed.add_field(name="Título", value=title)
                        await message.channel.send(embed=embed)
                    else:
                        try:
                            err_json = await resp.json()
                            err_msg = err_json.get("message", "Error desconocido")
                        except Exception:
                            err_msg = await resp.text()
                            err_msg = err_msg[:150]  # Limitar tamaño
                        await message.channel.send(f"❌ Error al crear tarea en GitHub (Código {resp.status}): {err_msg}")

        # Comando !repo [usuario/proyecto] o !repo para ver el actual
        if message.content.startswith("!repo"):
            args = message.content[5:].strip()
            if args:
                # Cambiar de repositorio
                if "/" not in args or len(args.split("/")) != 2:
                    await message.channel.send("❌ Formato incorrecto. Uso: `!repo usuario/repositorio` o simplemente `!repo` para ver el actual.")
                    return

                old_repo = self.github_repo
                self.github_repo = args

                async with aiohttp.ClientSession() as session:
                    url = f"https://api.github.com/repos/{self.github_repo}/commits?per_page=3"
                    headers = {}
                    if GITHUB_TOKEN:
                        headers["Authorization"] = f"token {GITHUB_TOKEN}"
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            # Guardar en disco para persistencia
                            try:
                                with open(self.config_path, "w", encoding="utf-8") as f:
                                    f.write(self.github_repo)
                            except Exception as e:
                                print(f"[ERROR] No se pudo guardar la configuración: {e}")

                            await message.channel.send(f"✅ Repositorio de trabajo cambiado a: `{self.github_repo}`")
                            commits = await resp.json()
                            embed = discord.Embed(
                                title=f"🚀 Últimos cambios en {self.github_repo}",
                                url=f"https://github.com/{self.github_repo}",
                                color=discord.Color.blue()
                            )
                            for c in commits:
                                msg = c["commit"]["message"].split("\n")[0]
                                author = c["commit"]["author"]["name"]
                                embed.add_field(name=msg, value=f"por **{author}**", inline=False)
                            await message.channel.send(embed=embed)
                        else:
                            # Revertir si falla la conexión o no existe
                            self.github_repo = old_repo
                            await message.channel.send(f"❌ Error al conectar con `{args}`. ¿Existe el repositorio y es público? Se ha mantenido el repositorio anterior: `{self.github_repo}`.")
            else:
                # Ver repositorio actual
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.github.com/repos/{self.github_repo}/commits?per_page=3"
                    headers = {}
                    if GITHUB_TOKEN:
                        headers["Authorization"] = f"token {GITHUB_TOKEN}"
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            commits = await resp.json()
                            embed = discord.Embed(
                                title=f"🚀 Repositorio activo: {self.github_repo}",
                                url=f"https://github.com/{self.github_repo}",
                                color=discord.Color.blue(),
                                description="Usa `!repo usuario/repositorio` para cambiar el repositorio de trabajo."
                            )
                            for c in commits:
                                msg = c["commit"]["message"].split("\n")[0]
                                author = c["commit"]["author"]["name"]
                                embed.add_field(name=msg, value=f"por **{author}**", inline=False)
                            await message.channel.send(embed=embed)
                        else:
                            await message.channel.send(f"❌ No se pudo obtener información del repositorio activo `{self.github_repo}`.")

        # Hilos automáticos en Showcase
        if message.channel.id == SHOWCASE_CH_ID:
            await message.create_thread(name=f"Discusión: {message.author.display_name}")

    # ─── AUTOROLES POR REACCIÓN ─────────────────────────────────────────────
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id: return
        guild = self.get_guild(payload.guild_id)
        emoji = str(payload.emoji)
        if emoji in self.role_map:
            role = discord.utils.get(guild.roles, name=self.role_map[emoji])
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.add_roles(role)
                print(f"[ROLES] {self.role_map[emoji]} asignado a {member.name}")

    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.user.id: return
        guild = self.get_guild(payload.guild_id)
        emoji = str(payload.emoji)
        if emoji in self.role_map:
            role = discord.utils.get(guild.roles, name=self.role_map[emoji])
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.remove_roles(role)
                print(f"[ROLES] {self.role_map[emoji]} removido de {member.name}")


bot = MasterBot()
bot.run(TOKEN)
