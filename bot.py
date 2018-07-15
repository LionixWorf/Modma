'''
MIT License

Copyright (c) 2017 Kyb3r

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

GUILD_ID = 0 # your guild id here

import discord
from discord.ext import commands
from urllib.parse import urlparse
import asyncio
import textwrap
import datetime
import time
import json
import sys
import os
import re
import string
import traceback
import io
import inspect
from contextlib import redirect_stdout


class Modmail(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=self.get_pre)
        self.uptime = datetime.datetime.utcnow()
        self._add_commands()

    def _add_commands(self):
        '''Adds commands automatically'''
        for attr in dir(self):
            cmd = getattr(self, attr)
            if isinstance(cmd, commands.Command):
                self.add_command(cmd)

    @property
    def token(self):
        '''Returns your token wherever it is'''
        try:
            with open('config.json') as f:
                config = json.load(f)
                if config.get('TOKEN') == "your_token_here":
                    if not os.environ.get('TOKEN'):
                        self.run_wizard()
                else:
                    token = config.get('TOKEN').strip('\"')
        except FileNotFoundError:
            token = None
        return os.environ.get('TOKEN') or token
    
    @staticmethod
    async def get_pre(bot, message):
        '''Returns the prefix.'''
        with open('config.json') as f:
            prefix = json.load(f).get('PREFIX')
        return os.environ.get('PREFIX') or prefix or 'm.'

    @staticmethod
    def run_wizard():
        '''Wizard for first start'''
        print('------------------------------------------')
        token = input('Enter your token:\n> ')
        print('------------------------------------------')
        data = {
                "TOKEN" : token,
            }
        with open('config.json','w') as f:
            f.write(json.dumps(data, indent=4))
        print('------------------------------------------')
        print('Restarting...')
        print('------------------------------------------')
        os.execv(sys.executable, ['python'] + sys.argv)

    @classmethod
    def init(cls, token=None):
        '''Starts the actual bot'''
        bot = cls()
        if token:
            to_use = token.strip('"')
        else:
            to_use = bot.token.strip('"')
        try:
            bot.run(to_use, activity=discord.Game(os.getenv('STATUS')), reconnect=True)
        except Exception as e:
            raise e

    async def on_connect(self):
        print('---------------')
        print('Modmail conectado!')
        status = os.getenv('STATUS')
        if status:
            print(f'Setting Status to {status}')
        else:
            print('No status set.')

    @property
    def guild_id(self):
        from_heroku = os.environ.get('GUILD_ID')
        return int(from_heroku) if from_heroku else GUILD_ID

    async def on_ready(self):
        '''Bot startup, sets uptime.'''
        self.guild = discord.utils.get(self.guilds, id=self.guild_id)
        print(textwrap.dedent(f'''
        ---------------
        Client is ready!
        ---------------
        Author: Kyb3r#7220
        ---------------
        Logged in as: {self.user}
        User ID: {self.user.id}
        ---------------
        '''))

    def overwrites(self, ctx, modrole=None):
        '''Permision overwrites for the guild.'''
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }

        if modrole:
            overwrites[modrole] = discord.PermissionOverwrite(read_messages=True)
        else:
            for role in self.guess_modroles(ctx):
                overwrites[role] = discord.PermissionOverwrite(read_messages=True)

        return overwrites

    def help_embed(self, prefix):
        em = discord.Embed(color=0x00FFFF)
        em.set_author(name='Mod Mail - Ajuda', icon_url=self.user.avatar_url)
        em.description = 'Este bot é uma implementação ModMail melhorada e traduzida para' \
                         ' a lingua Portuguesa. Este bot não salva dados e utiliza tópicos ' \
                         ' para armazenamento e sincronização.' 
                 

        cmds = f'`{prefix}setup [Cargo] <- (opcional)` - Configura cargos que irão ter permissão de usar o ModMail.\n' \
               f'`{prefix}reply <mensagem...>` - Envia a mensagem desejada a quem iniciou a sessão.\n' \
               f'`{prefix}close` - Fecha a sessão de conversa com o membro e apaga a sala.\n' \
               f'`{prefix}disable` - Desabilita o ModMail e fecha todas as salas em execução.\n' \
               f'`{prefix}customstatus` - Muda o status do bot.' \
               f'`{prefix}block` - Bloqueia um usuario de usar o ModMail!' \
               f'`{prefix}unblock` - Desbloqueia um usuario de usar o ModMail!'

        warn = 'Não altere nada manualmente nas configurações desta sala. ' \
               'Ao modificar algo nesta sala, ocorrerá um erro nas configurações do bot.'
        em.add_field(name='Commands', value=cmds)
        em.add_field(name='Warning', value=warn)
        em.add_field(name='Github', value='https://github.com/verixx/modmail')
        em.set_footer(text='Repositorio do bot para configurações ocultas!')

        return em

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, *, modrole: discord.Role=None):
        '''Configura cargos que possam acessar o ModMail.'''
        if discord.utils.get(ctx.guild.categories, name='Mod Mail'):
            return await ctx.send('Este servidor já está configurado.')

        categ = await ctx.guild.create_category(
            name='Mod Mail', 
            overwrites=self.overwrites(ctx, modrole=modrole)
            )
        await categ.edit(position=0)
        c = await ctx.guild.create_text_channel(name='bot-info', category=categ)
        await c.edit(topic='Adicione manualmente os ID do usuario para bloquea-lo.\n\n'
                           'Bloqueado\n-------\n\n')
        await c.send(embed=self.help_embed(ctx.prefix))
        await ctx.send('Servidor configurado com sucesso.')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        '''Feche todos os tópicos e desabilite o ModMail.'''
        categ = discord.utils.get(ctx.guild.categories, name='Mod Mail')
        if not categ:
            return await ctx.send('Este servidor não está configurado.')
        for category, channels in ctx.guild.by_category():
            if category == categ:
                for chan in channels:
                    if 'User ID:' in str(chan.topic):
                        user_id = int(chan.topic.split(': ')[1])
                        user = self.get_user(user_id)
                        await user.send(f'Resposta enviada para analise.')
                    await chan.delete()
        await categ.delete()
        await ctx.send('ModMail Desativado.')


    @commands.command(name='close')
    @commands.has_permissions(manage_channels=True)
    async def _close(self, ctx):
        '''Feche a sessão atual.'''
        if 'User ID:' not in str(ctx.channel.topic):
            return await ctx.send('Isto não é um tópico ModMail.')
        user_id = int(ctx.channel.topic.split(': ')[1])
        user = self.get_user(user_id)
        em = discord.Embed(title='Obrigado!')
        em.description = f'**Sua resposta foi enviada para analise!**'
        em.color = discord.Color.red()
        try:
            await user.send(embed=em)
        except:
            pass
        await ctx.channel.delete()

    @commands.command()
    async def ping(self, ctx):
        """Pong! Veja a lentencia do Bot."""
        em = discord.Embed()
        em.title ='Pong!'
        em.description = f'{self.ws.latency * 1000:.4f} ms'
        em.color = 0x00FF00
        await ctx.send(embed=em)

    def guess_modroles(self, ctx):
        '''Encontra funções que tem permissão no tópico'''
        for role in ctx.guild.roles:
            if role.permissions.manage_guild:
                yield role

    def format_info(self, message):
        '''Obter informações sobre um membro do servidor.'''
        user = message.author
        server = self.guild
        member = self.guild.get_member(user.id)
        avi = user.avatar_url
        time = datetime.datetime.utcnow()
        desc = 'Sessão Iniciada!'
        color = 0

        if member:
            roles = sorted(member.roles, key=lambda c: c.position)
            rolenames = ', '.join([r.name for r in roles if r.name != "@everyone"]) or 'None'
            member_number = sorted(server.members, key=lambda m: m.joined_at).index(member) + 1
            for role in roles:
                if str(role.color) != "#000000":
                    color = role.color

        em = discord.Embed(colour=color, description=desc, timestamp=time)

        em.add_field(name='Conta criada', value=str((time - user.created_at).days)+' dias atraz.')
        em.set_footer(text='ID do usuario: '+str(user.id))
        em.set_thumbnail(url=avi)
        em.set_author(name=user, icon_url=server.icon_url)
      

        if member:
            em.add_field(name='Entro no Servidor', value=str((time - member.joined_at).days)+' dias atraz.')
            em.add_field(name='Membro.',value=str(member_number),inline = True)
            em.add_field(name='Nome', value=member.nick, inline=True)
            em.add_field(name='Cargos', value=rolenames, inline=True)
        
        em.add_field(name='Messagem', value=message.content, inline=False)

        return em

    async def send_mail(self, message, channel, mod):
        author = message.author
        fmt = discord.Embed()
        fmt.description = message.content
        fmt.timestamp = message.created_at

        urls = re.findall(r'(https?://[^\s]+)', message.content)

        types = ['.png', '.jpg', '.gif', '.jpeg', '.webp']

        for u in urls:
            if any(urlparse(u).path.endswith(x) for x in types):
                fmt.set_image(url=u)
                break

        if mod:
            fmt.color=discord.Color.green()
            fmt.set_footer(text='Moderador')
        else:
            fmt.color=discord.Color.gold()
            fmt.set_author(name=str(author), icon_url=author.avatar_url)
            fmt.set_footer(text='User')

        embed = None

        if message.attachments:
            fmt.set_image(url=message.attachments[0].url)

        await channel.send(embed=fmt)

    async def process_reply(self, message):
        try:
            await message.delete()
        except discord.errors.NotFound:
            pass
        await self.send_mail(message, message.channel, mod=True)
        user_id = int(message.channel.topic.split(': ')[1])
        user = self.get_user(user_id)
        await self.send_mail(message, user, mod=True)

    def format_name(self, author):
        name = author.name
        new_name = ''
        for letter in name:
            if letter in string.ascii_letters + string.digits:
                new_name += letter
        if not new_name:
            new_name = 'null'
        new_name += f'-{author.discriminator}'
        return new_name

    @property
    def blocked_em(self):
        em = discord.Embed(title='Menssagem não enviada!', color=discord.Color.red())
        em.description = 'Você foi bloqueado de usar o ModMail.'
        return em

    async def process_modmail(self, message):
        '''Processa mensagens enviadas pelo Bot.'''
        try:
            await message.add_reaction('✅')
        except:
            pass

        guild = self.guild
        author = message.author
        topic = f'User ID: {author.id}'
        channel = discord.utils.get(guild.text_channels, topic=topic)
        categ = discord.utils.get(guild.categories, name='Mod Mail')
        top_chan = categ.channels[0] #bot-info
        blocked = top_chan.topic.split('Blocked\n-------')[1].strip().split('\n')
        blocked = [x.strip() for x in blocked]

        if str(message.author.id) in blocked:
            return await message.author.send(embed=self.blocked_em)

        em = discord.Embed(title='Vagas para Moderação abertas!')
        em.description = '**Para Participar Informe:**\n \n``1-Sua idade.\n2-Por que quer ser um moderador.\n3-Oque fazer para mudar o grupo.`` \n\n **Boa Sorte!**'
        em.color = discord.Color.green()

        if channel is not None:
            await self.send_mail(message, channel, mod=False)
        else:
            await message.author.send(embed=em)
            channel = await guild.create_text_channel(
                name=self.format_name(author),
                category=categ
                )
            await channel.edit(topic=topic)
            await channel.send('@here', embed=self.format_info(message))

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)
        if isinstance(message.channel, discord.DMChannel):
            await self.process_modmail(message)

    @commands.command()
    async def reply(self, ctx, *, msg):
        '''Responder aos usuarios usando este comando.'''
        categ = discord.utils.get(ctx.guild.categories, id=ctx.channel.category_id)
        if categ is not None:
            if categ.name == 'Mod Mail':
                if 'User ID:' in ctx.channel.topic:
                    ctx.message.content = msg
                    await self.process_reply(ctx.message)

    @commands.command(name="customstatus", aliases=['status', 'presence'])
    @commands.has_permissions(administrator=True)
    async def _status(self, ctx, *, message):
        '''Define um status personalizado para o Bot.'''
        if message == 'clear':
            return await self.change_presence(activity=None)
        await self.change_presence(activity=discord.Game(message))
        await ctx.send(f"Meu novo status é **{message}**")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def block(self, ctx, id=None):
        '''Bloqueia o usuario de usar o ModMail.'''
        if id is None:
            if 'User ID:' in str(ctx.channel.topic):
                id = ctx.channel.topic.split('User ID: ')[1].strip()
            else:
                return await ctx.send('No User ID provided.')

        categ = discord.utils.get(ctx.guild.categories, name='Mod Mail')
        top_chan = categ.channels[0] #bot-info
        topic = str(top_chan.topic)
        topic += id + '\n'

        if id not in top_chan.topic:  
            await top_chan.edit(topic=topic)
            await ctx.send('Usuario bloqueado com sucesso!')
        else:
            await ctx.send('Usuario já está bloqueado.')

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unblock(self, ctx, id=None):
        '''Desbloqueia um usuario para usar o ModMail.'''
        if id is None:
            if 'User ID:' in str(ctx.channel.topic):
                id = ctx.channel.topic.split('User ID: ')[1].strip()
            else:
                return await ctx.send('No User ID provided.')

        categ = discord.utils.get(ctx.guild.categories, name='Mod Mail')
        top_chan = categ.channels[0] #bot-info
        topic = str(top_chan.topic)
        topic = topic.replace(id+'\n', '')

        if id in top_chan.topic:
            await top_chan.edit(topic=topic)
            await ctx.send('Usuario desblloqueado com sucesso!')
        else:
            await ctx.send('O usuario ainda não está bloqueado.')

    @commands.command(hidden=True, name='eval')
    async def _eval(self, ctx, *, body: str):
        """Evaluates python code"""
        allowed = [int(x) for x in os.getenv('OWNERS', '').split(',')]
        if ctx.author.id not in allowed: 
            return
        
        env = {
            'bot': self,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'source': inspect.getsource
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()
        err = out = None

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            err = await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
            return await err.add_reaction('\u2049')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            err = await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            if ret is None:
                if value:
                    try:
                        out = await ctx.send(f'```py\n{value}\n```')
                    except:
                        await ctx.send('```Result is too long to send.```')
            else:
                self._last_result = ret
                try:
                    out = await ctx.send(f'```py\n{value}{ret}\n```')
                except:
                    await ctx.send('```Result is too long to send.```')
        if out:
            await ctx.message.add_reaction('\u2705') #tick
        if err:
            await ctx.message.add_reaction('\u2049') #x
        else:
            await ctx.message.add_reaction('\u2705')

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')
        
if __name__ == '__main__':
    Modmail.init()
