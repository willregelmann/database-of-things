"""
Test multi-model LLM provider support.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

console = Console()

# Load environment variables
load_dotenv()


async def test_google_llm():
    """Test Google Gemini LLM."""
    console.print("\n[bold cyan]Testing Google Gemini LLM[/bold cyan]")

    # Set provider to google
    os.environ["LLM_PROVIDER"] = "google"

    # Import after setting env var
    from core.llm import get_llm

    try:
        # Check if API key is set
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key == "your-google-api-key-here":
            console.print(
                "  ⚠️  GOOGLE_API_KEY not set - skipping actual API call"
            )
            console.print("  ℹ️  To test API calls, set GOOGLE_API_KEY in .env")

            # Still test initialization (will fail if package not installed)
            try:
                llm = get_llm()
                console.print(f"  ✅ LLM class loaded: {llm.__class__.__name__}")
            except ValueError as e:
                if "GOOGLE_API_KEY not set" in str(e):
                    console.print("  ✅ Validation working (API key check)")
                else:
                    raise
        else:
            llm = get_llm()
            console.print(f"  ✅ LLM initialized: {llm.__class__.__name__}")

            # Test invocation with real key
            response = llm.invoke("Say 'Hello from Gemini!' in exactly 4 words.")
            console.print(f"  ✅ LLM response: {response.content}")

    except Exception as e:
        console.print(f"  ❌ Error: {e}")
        raise


async def test_mem0_config_selection():
    """Test Mem0 config auto-selection based on provider."""
    console.print("\n[bold cyan]Testing Mem0 Config Selection[/bold cyan]")

    # Set provider to google
    os.environ["LLM_PROVIDER"] = "google"

    # Import after setting env var
    from core.memory import TieredMemoryManager

    try:
        # Create manager
        manager = TieredMemoryManager(curator_id="test-multi-model")

        # Check config path
        config_path = manager._get_mem0_config_path()
        console.print(f"  ✅ Config path: {config_path}")

        # Verify it's the Google config
        assert "google" in str(config_path), f"Expected Google config, got {config_path}"
        console.print(f"  ✅ Correct config selected for provider: google")

        # Verify config exists
        assert Path(config_path).exists(), f"Config file doesn't exist: {config_path}"
        console.print(f"  ✅ Config file exists")

    except Exception as e:
        console.print(f"  ❌ Error: {e}")
        raise


async def test_provider_override():
    """Test provider override in get_llm()."""
    console.print("\n[bold cyan]Testing Provider Override[/bold cyan]")

    # Set default provider to google
    os.environ["LLM_PROVIDER"] = "google"

    from core.llm import get_llm

    try:
        # Override with specific model
        llm = get_llm(provider="google", model="gemini-2.0-flash-exp")
        console.print(f"  ✅ LLM with override: {llm.__class__.__name__}")

    except Exception as e:
        console.print(f"  ❌ Error: {e}")
        raise


async def main():
    """Run all tests."""
    console.print("[bold magenta]Multi-Model Provider Tests[/bold magenta]")

    try:
        await test_google_llm()
        await test_mem0_config_selection()
        await test_provider_override()

        console.print("\n[bold green]✅ All multi-model tests passed![/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]❌ Tests failed: {e}[/bold red]")
        raise


if __name__ == "__main__":
    asyncio.run(main())
