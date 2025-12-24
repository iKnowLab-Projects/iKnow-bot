"""
Discord Bot with LLM Integration
Refactored with OOP design patterns for better maintainability
"""
import discord
from discord.ext import commands
import openai
import aiohttp
import os
import base64
import fitz  # PyMuPDF
import uuid
import re
from bs4 import BeautifulSoup
import yaml
import datetime
import pytz
import asyncio
from typing import List, Dict, Optional, Any

from config import BotConfig


# ==========================================
# 🔧 LLM Client
# ==========================================
class LLMClient:
    """Handles all interactions with OpenAI/LiteLLM API"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.client = openai.AsyncOpenAI(
            base_url=config.openai_api_base,
            api_key=config.openai_api_key
        )
    
    async def get_response(
        self, 
        messages: List[Dict[str, Any]], 
        temperature: float = 0.7
    ) -> str:
        """Get response from LLM"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ 모델 오류: {str(e)}"


# ==========================================
# 💬 Message Formatter
# ==========================================
class MessageFormatter:
    """Formats messages and handles thought process display"""
    
    def __init__(self, config: BotConfig):
        self.config = config
    
    def format_thought(self, content: str) -> str:
        """Format thought process based on configuration"""
        if '</think>' not in content:
            return content.strip()
        
        # Split by </think> - everything before is thinking, everything after is answer
        parts = content.split('</think>', 1)
        think = parts[0].strip()
        
        think = re.sub(r'^<think>\s*', '', think, flags=re.DOTALL).strip()
        
        answer = parts[1].strip() if len(parts) > 1 else ""
        
        if self.config.show_thought_process == "hidden":
            return answer
        elif self.config.show_thought_process == "block":
            return f"**💭 사고 과정**\n> " + think[:900].replace("\n", "\n> ") + f"\n\n{answer}"
        else:  # "spoiler" or default
            separator = "\n\n" if answer else ""
            return f"||**💭 사고 과정**\n{think[:900]}||{separator}{answer}"
    
    @staticmethod
    async def send_split_message(ctx, text: str):
        """Send message in chunks to avoid Discord 2000 char limit"""
        if len(text) <= 2000:
            await ctx.send(text)
        else:
            chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for chunk in chunks:
                await ctx.send(chunk)


# ==========================================
# 🌐 Web Fetcher
# ==========================================
class WebFetcher:
    """Handles web content fetching and image encoding"""
    
    @staticmethod
    async def encode_image(url: str) -> Optional[str]:
        """Encode image from URL to base64"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return base64.b64encode(await resp.read()).decode('utf-8')
        except Exception:
            pass
        return None
    
    @staticmethod
    async def fetch_text(url: str) -> Optional[str]:
        """Fetch and extract text content from web page"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    for s in soup(["script", "style", "nav", "footer"]):
                        s.decompose()
                    return soup.get_text(separator='\\n')[:15000]
        except Exception:
            return None


# ==========================================
# 📝 Report Generator
# ==========================================
class ReportGenerator:
    """Generates and saves HTML reports"""
    
    def __init__(self, config: BotConfig):
        self.config = config
    
    async def save_report(
        self, 
        title: str, 
        content: str, 
        images_html: str = ""
    ) -> str:
        """Save report as HTML and return URL"""
        report_id = str(uuid.uuid4())
        os.makedirs(self.config.reports_dir, exist_ok=True)
        
        html = f"""<!DOCTYPE html><html><head><title>{title}</title><meta charset='utf-8'>
        <style>body{{font-family:sans-serif;max-width:900px;margin:0 auto;padding:20px;line-height:1.6;}}
        pre{{background:#f4f4f4;padding:15px;overflow-x:auto;border-radius:5px;white-space:pre-wrap;}}
        img{{max-width:100%;margin:10px 0;border:1px solid #ddd;}}</style></head>
        <body><h1>{title}</h1>{content}<hr><h2>📊 Figures</h2>{images_html}</body></html>"""
        
        with open(f"{self.config.reports_dir}/{report_id}.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        return f"{self.config.web_viewer_url}/{report_id}.html"


# ==========================================
# 🗓️ Conference Deadline Checker
# ==========================================
class ConferenceDeadlineChecker:
    """Checks and parses conference deadlines from CCF"""
    
    def __init__(self, config: BotConfig):
        self.config = config
    
    def parse_conference(self, data: Dict) -> Optional[Dict]:
        """Parse conference data and return next upcoming deadline"""
        try:
            if isinstance(data, list):
                data = data[0]
            
            confs = data.get('confs', [])
            if not confs:
                return None
            
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.datetime.now(kst)
            upcoming_deadlines = []
            
            for conf in confs:
                timeline = conf.get('timeline', [])
                if not timeline:
                    continue
                
                tz_str = conf.get('timezone', 'UTC')
                if 'UTC-12' in tz_str or 'AoE' in tz_str:
                    tz = pytz.timezone('Etc/GMT+12')
                else:
                    try:
                        tz = pytz.timezone(tz_str)
                    except Exception:
                        tz = pytz.UTC
                
                for item in timeline:
                    date_str = item.get('deadline')
                    if not date_str:
                        continue
                    
                    try:
                        local_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        local_dt = tz.localize(local_dt)
                        kst_dt = local_dt.astimezone(kst)
                        
                        if kst_dt > now_kst:
                            diff = kst_dt - now_kst
                            upcoming_deadlines.append({
                                'title': data.get('title'),
                                'desc': data.get('description', ''),
                                'year': conf.get('year'),
                                'deadline': kst_dt,
                                'd_day': diff.days,
                                'hours': diff.seconds // 3600,
                                'link': conf.get('link', ''),
                                'comment': item.get('comment', '')
                            })
                    except Exception:
                        continue
            
            if not upcoming_deadlines:
                return None
            
            upcoming_deadlines.sort(key=lambda x: x['deadline'])
            return upcoming_deadlines[0]
        
        except Exception:
            return None
    
    async def fetch_all_deadlines(self) -> List[Dict]:
        """Fetch deadlines from all configured conferences"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for conf_id in self.config.target_conferences:
                for cat in self.config.ccf_categories:
                    url = self.config.ccf_url_template.format(category=cat, id=conf_id)
                    tasks.append(session.get(url))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            results = []
            seen_ids = set()
            
            for resp in responses:
                if isinstance(resp, Exception):
                    continue
                
                if resp.status == 200:
                    try:
                        data = yaml.safe_load(await resp.text())
                        if isinstance(data, list) and len(data) > 0:
                            data = data[0]
                        
                        title = data.get('title')
                        if not title or title in seen_ids:
                            continue
                        
                        info = self.parse_conference(data)
                        if info:
                            results.append(info)
                            seen_ids.add(title)
                    except Exception:
                        continue
            
            return sorted(results, key=lambda x: x['deadline'])


# ==========================================
# 🤖 Discord Bot
# ==========================================
class DiscordBot(commands.Bot):
    """Main Discord bot with LLM integration"""
    
    def __init__(self, config: BotConfig):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=config.command_prefix, intents=intents)
        
        self.config = config
        self.llm = LLMClient(config)
        self.formatter = MessageFormatter(config)
        self.web_fetcher = WebFetcher()
        self.report_gen = ReportGenerator(config)
        self.deadline_checker = ConferenceDeadlineChecker(config)
        
        self._register_commands()
    
    def _register_commands(self):
        """Register all bot commands"""
        
        @self.event
        async def on_ready():
            print(f'✅ Bot Logged in as {self.user}')
        
        @self.command(name="deadlines")
        async def check_deadlines(ctx):
            await ctx.message.add_reaction("⏳")
            
            results = await self.deadline_checker.fetch_all_deadlines()
            
            if not results:
                await ctx.send("📅 예정된 주요 학회 마감일이 없습니다.")
            else:
                embed = discord.Embed(title="📅 주요 학회 마감일 (KST 기준)", color=0xff9900)
                for res in results:
                    d_str = f"D-{res['d_day']}" if res['d_day'] > 0 else "🚨 D-DAY"
                    val = f"**마감**: {res['deadline'].strftime('%Y-%m-%d %H:%M')}\\n"
                    val += f"**남은 시간**: {res['d_day']}일 {res['hours']}시간"
                    if res['link']:
                        val += f"\\n[홈페이지]({res['link']})"
                    embed.add_field(
                        name=f"🏆 {res['title']} {res['year']} ({d_str})",
                        value=val,
                        inline=False
                    )
                await ctx.send(embed=embed)
            
            await ctx.message.remove_reaction("⏳", self.user)

        @self.command(name="Hi")
        async def bot_test(ctx):
            msg = await ctx.send("Greetings...")
            await msg.delete()
            await self.formatter.send_split_message(ctx, "Hello World! o((>ω< ))o)")
        
        @self.command(name="chat")
        async def simple_chat(ctx, *, text=None):
            if not text and not ctx.message.attachments:
                return await ctx.send("❓ 내용을 입력해주세요.")
            
            msg = await ctx.send("🤔 생각 중...")
            
            messages = [{"role": "system", "content": "너는 도움이 되는 AI 어시스턴트야."}]
            
            # Check for URLs
            urls = re.findall(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                text or ""
            )
            if urls:
                web_content = await self.web_fetcher.fetch_text(urls[0])
                if web_content:
                    messages[0]["content"] += f"\\n\\n[참고 자료]\\n{web_content}"
            
            # Build content with text and images
            content_payload = [{"type": "text", "text": text or "이 내용을 설명해줘."}]
            if ctx.message.attachments:
                for att in ctx.message.attachments:
                    if att.content_type and att.content_type.startswith('image'):
                        b64 = await self.web_fetcher.encode_image(att.url)
                        if b64:
                            content_payload.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                            })
            
            messages.append({"role": "user", "content": content_payload})
            response = await self.llm.get_response(messages)
            formatted = self.formatter.format_thought(response)
            
            await msg.delete()
            await self.formatter.send_split_message(ctx, formatted)
        
        @self.command(name="arxiv")
        async def arxiv_analysis(ctx, url: str):
            await ctx.message.add_reaction("📑")
            if "abs" in url:
                url = url.replace("abs", "pdf")
            if not url.endswith(".pdf"):
                url += ".pdf"
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            raise Exception("다운로드 실패")
                        pdf_bytes = await resp.read()
                
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                text = "".join([p.get_text() for p in doc])[:40000]
                
                prompt = f"""다음 논문을 분석하고 아래 항목에 대해 반드시 한글로 답변해주세요.
                각 요소는 bullet point로 정리하고, 하이픈 대신 • 사용

                1. 제목 및 저자
                2. 주요 컨트리뷰션
                3. 연구 방법론 요약
                4. 주요 결과
                5. 한계점
                6. Future works 추천

                ===논문 내용===
                {text}"""
                
                response = await self.llm.get_response([{"role": "user", "content": prompt}])
                formatted = self.formatter.format_thought(response)
                
                await ctx.send(f"📑 **Arxiv 분석**: {url}")
                await self.formatter.send_split_message(ctx, formatted)
                
            except Exception as e:
                await ctx.send(f"❌ 오류: {str(e)}")
        
        @self.command(name="review")
        async def review_pdf(ctx):
            if not ctx.message.attachments:
                return await ctx.send("❌ PDF를 첨부해주세요.")
            
            msg = await ctx.send("🔄 리포트 생성 중...")
            
            try:
                att = ctx.message.attachments[0]
                async with aiohttp.ClientSession() as session:
                    data = await session.get(att.url)
                    pdf_bytes = await data.read()
                
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                full_text = ""
                images_html = ""
                
                for i, page in enumerate(doc):
                    full_text += page.get_text()
                    for img in page.get_images(full=True):
                        try:
                            base = doc.extract_image(img[0])
                            b64 = base64.b64encode(base["image"]).decode("utf-8")
                            images_html += f"<img src='data:image/png;base64,{b64}'><br>"
                        except Exception:
                            pass
                
                prompt = f"논문 상세 분석 리포트를 마크다운으로 작성해줘. (서론, 기여점, 방법론, 실험, 결론)\\n내용: {full_text[:50000]}"
                detail = await self.llm.get_response([{"role": "user", "content": prompt}])
                formatted = self.formatter.format_thought(detail)
                link = await self.report_gen.save_report(
                    f"Review: {att.filename}",
                    f"<pre>{formatted}</pre>",
                    images_html
                )
                
                embed = discord.Embed(
                    title="분석 완료",
                    description=f"[👉 전체 리포트 보기]({link})",
                    color=0x00ff00
                )
                await msg.delete()
                await ctx.send(embed=embed)
            
            except Exception as e:
                await msg.edit(content=f"❌ 실패: {str(e)}")
        
        @self.command(name="websumm")
        async def web_summary(ctx, url: str):
            await ctx.message.add_reaction("🌐")
            content = await self.web_fetcher.fetch_text(url)
            if not content:
                return await ctx.send("❌ 읽기 실패")
            
            prompt = f"웹사이트 내용을 요약해줘:\\n{content}"
            resp = await self.llm.get_response([{"role": "user", "content": prompt}])
            formatted = self.formatter.format_thought(resp)
            
            await ctx.send(f"🌐 **웹 요약**: {url}")
            await self.formatter.send_split_message(ctx, formatted)
            await ctx.message.remove_reaction("🌐", self.user)
        
        @self.event
        async def on_message(message):
            if message.author == self.user:
                return
            
            if self.user.mentioned_in(message) or (
                message.reference and message.reference.resolved.author == self.user
            ):
                async with message.channel.typing():
                    history = []
                    async for m in message.channel.history(limit=6):
                        if m.id == message.id:
                            continue
                        role = "assistant" if m.author == self.user else "user"
                        content = m.content.replace(f'<@{self.user.id}>', '').strip()
                        if content:
                            history.insert(0, {"role": role, "content": content})
                    
                    curr = message.content.replace(f'<@{self.user.id}>', '').strip()
                    history.append({"role": "user", "content": curr})
                    response = await self.llm.get_response(history)
                    formatted = self.formatter.format_thought(response)
                    await self.formatter.send_split_message(message.channel, formatted)
            
            await self.process_commands(message)


# ==========================================
# 🚀 Main Entry Point
# ==========================================
def main():
    """Main entry point"""
    config = BotConfig.from_env()
    bot = DiscordBot(config)
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
