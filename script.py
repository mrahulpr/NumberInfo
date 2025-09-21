import requests
import time
import sys
import itertools
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import base64 # <-- Make sure this import is there

console = Console()

BANNER = r"""
███╗░░██╗███████╗██╗░░██╗██╗░░░██╗░██████╗
████╗░██║██╔════╝╚██╗██╔╝██║░░░██║██╔════╝
██╔██╗██║█████╗░░░╚███╔╝░██║░░░██║╚█████╗░
██║╚████║██╔══╝░░░██╔██╗░██║░░░██║░╚═══██╗
██║░╚███║███████╗██╔╝╚██╗╚██████╔╝██████╔╝
╚═╝░░╚══╝╚══════╝╚═╝░░╚═╝░╚═════╝░╚═════╝░
"""

# 🔑 Yeh woh encrypted strings hain
# Ab API URL aur API Key seedhe-seedhe nahi dikhenge
ENCODED_API_URL = "aHR0cDovLzQ2LjYyLjEzNS4xMjU6NTAwMC9hcGkvbW9iaWxl"
ENCODED_API_KEY = "TmlraGlsZXNoVjI="

# Decode karne ke functions
def decode_string(encoded_data):
    return base64.b64decode(encoded_data).decode('utf-8')

# 🔹 Typing effect
def typing_effect(text, delay=0.03, style="bold white"):
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    console.print("", style=style)

# 🔹 Loader animation
def animate_loader(text, seconds=2, symbol_cycle=None):
    if symbol_cycle is None:
        symbol_cycle = itertools.cycle(["▒","▓","█","▓","▒"])
    end_time = time.time() + seconds
    while time.time() < end_time:
        sys.stdout.write(f"\r{text} {next(symbol_cycle)}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * (len(text)+5) + "\r")

def search_user(query: str) -> None:
    try:
        animate_loader("▒▒▒ Accessing Database...", 2)
        animate_loader("▣ Fetching Information...", 2)
        animate_loader("◉ Finalizing Request...", 2)
        typing_effect("✔ Process Completed\n", 0.04, "bold green")

        # 🚀 Yahan encoded strings ko decode kiya ja raha hai
        API_URL = decode_string(ENCODED_API_URL)
        API_KEY = decode_string(ENCODED_API_KEY)

        params = {"apikey": API_KEY, "query": query}
        response = requests.get(API_URL, params=params, timeout=8)
        response.raise_for_status()
        data = response.json()

        if not data:
            console.print(Panel("⚠️ No results found", style="bold red"))
            return

        for idx, user in enumerate(data, 1):
            header = Text(f"▰▰▰ Result {idx} ▰▰▰", style="bold cyan")
            console.print(Panel.fit(header, style="bold magenta"))

            console.print(f"[bold yellow]◆ Name        :[/] [cyan]{user.get('name','Not Available').strip()}[/]")
            console.print(f"[bold yellow]◈ Father's    :[/] [green]{user.get('fname','Not Available').strip()}[/]")
            console.print(f"[bold yellow]◉ Address     :[/] [green]{user.get('address','Not Available').replace('!', ', ')}[/]")
            console.print(f"[bold yellow]➲ Mobile      :[/] [red]{user.get('mobile','Not Available')}[/]")
            console.print(f"[bold yellow]✪ Aadhaar     :[/] [magenta]{user.get('id','Not Available')}[/]")
            console.print(f"[bold yellow]✦ Circle      :[/] [bright_cyan]{user.get('circle','Not Available')}[/]\n")

        footer = Text(f"✺ Powered by Nexus ⚡ Wraith | {data[0].get('credit','No Credit')} ✺", style="bold green")
        console.print(Panel.fit(footer, style="bold blue"))

    except requests.exceptions.HTTPError as e:
        console.print(f"☢ Network error: {e.response.status_code}", style="bold red")
    except requests.exceptions.RequestException:
        console.print("☢ Network error: Connection Failed", style="bold red")
    except ValueError:
        console.print("☠ Invalid response format from API.", style="bold red")
    except Exception as e:
        console.print(f"An unexpected error occurred: {e}", style="bold red")


if __name__ == "__main__":
    console.print(Panel.fit(BANNER, title="🚀 Nexus Search Tool 🚀", style="bold green"))
    query = console.input("[bold green]➤ Enter search query: [/]")
    search_user(query)