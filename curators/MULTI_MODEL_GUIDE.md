# Multi-Model Support Guide

The curator framework supports multiple LLM providers, allowing you to choose based on your needs: cost, context window, performance, or features.

## Supported Providers

### 1. Google Gemini (Recommended for Curators) ⭐

**Why Gemini for Curators:**
- **Massive context window**: 2M+ tokens (perfect for processing large datasets)
- **Cost-effective**: ~15x cheaper than GPT-4 for long contexts
- **Fast**: Optimized for throughput
- **Great for**: Processing API responses, analyzing large collections, maintaining extensive memory

**Models:**
- `gemini-2.0-flash-exp` - Latest, fastest, 2M context (Free tier available)
- `gemini-1.5-pro` - Production-ready, 2M context
- `gemini-1.5-flash` - Fast, 1M context

**Pricing** (as of Nov 2025):
- Free tier: 1,500 requests/day (gemini-2.0-flash-exp)
- Paid: $0.075 per 1M input tokens (128K context)

### 2. OpenAI GPT

**Why OpenAI:**
- **Strong reasoning**: Best for complex logic
- **Structured outputs**: Excellent JSON generation
- **Proven reliability**: Production-ready
- **Great for**: Complex decision-making, code generation

**Models:**
- `gpt-4o` - Multimodal, 128K context
- `gpt-4o-mini` - Cost-effective, 128K context
- `gpt-4-turbo` - Previous generation, 128K context

**Pricing**:
- gpt-4o-mini: $0.15 per 1M input tokens
- gpt-4o: $2.50 per 1M input tokens

### 3. Anthropic Claude

**Why Claude:**
- **Long context**: 200K tokens (Claude 3.5)
- **Safety-focused**: Great guardrails
- **Strong analysis**: Excellent for research tasks
- **Great for**: Text analysis, careful reasoning

**Models:**
- `claude-3-5-sonnet-20241022` - Latest, 200K context
- `claude-3-opus` - Most capable, 200K context

**Pricing**:
- Claude 3.5 Sonnet: $3.00 per 1M input tokens

## Quick Setup

### Install Provider Dependencies

Choose one or more providers:

```bash
# Install Google Gemini (recommended)
pip install -e '.[google]'

# Or OpenAI
pip install -e '.[openai]'

# Or Anthropic
pip install -e '.[anthropic]'

# Or all of them
pip install -e '.[all-providers]'
```

### Configure Provider

Edit `.env`:

```bash
# Choose your provider
LLM_PROVIDER=google  # or openai, anthropic

# Add your API keys
GOOGLE_API_KEY=your-google-key-here      # For main LLM
OPENAI_API_KEY=your-openai-key-here      # Also required for Google (hybrid approach)
```

**Note**: When using `LLM_PROVIDER=google`, you need BOTH Google and OpenAI API keys due to the hybrid approach (see "Hybrid Approach for Google Provider" section below).

### Get API Keys

**Google Gemini:**
1. Visit https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy key to `.env`
4. Free tier: No credit card required!

**OpenAI:**
1. Visit https://platform.openai.com/api-keys
2. Create new key
3. Add credit card (pay-as-you-go)

**Anthropic:**
1. Visit https://console.anthropic.com/
2. Create API key
3. Add payment method

## Configuration Examples

### Gemini (2M Token Context)

**.env:**
```bash
LLM_PROVIDER=google
GOOGLE_API_KEY=AIzaSy...
GOOGLE_MODEL=gemini-2.0-flash-exp
```

**Use case**: Processing entire Pokemon TCG API responses in one go, maintaining extensive memory across runs.

### OpenAI (Structured Output)

**.env:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

**Use case**: Complex decision-making, when you need reliable JSON structures.

### Claude (Careful Analysis)

**.env:**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

**Use case**: Detailed analysis of collection metadata, careful data validation.

## Important: Hybrid Approach for Google Provider

**When using Google Gemini as your LLM provider, Mem0 (memory system) uses OpenAI for memory operations.**

### Why the Hybrid Approach?

Due to dependency conflicts between `langchain-google-genai` and `google-generativeai` (which Mem0's Gemini provider requires), we use a hybrid setup:

- **Main LLM (LangChain)**: Google Gemini 2.0 Flash (2M context, cost-effective)
- **Memory System (Mem0)**: OpenAI GPT-4o-mini (for memory extraction/summarization)

### What This Means for You

1. **You need BOTH API keys** when using Google provider:
   ```bash
   GOOGLE_API_KEY=your-google-key-here    # For main LLM
   OPENAI_API_KEY=your-openai-key-here    # For Mem0 memory operations
   ```

2. **Cost implications**:
   - 95%+ of tokens go through Google Gemini (cheap)
   - Only memory operations use OpenAI (minimal usage)
   - Overall cost is still ~90% cheaper than pure OpenAI

3. **Installation**: The `google` provider automatically includes OpenAI:
   ```bash
   pip install -e '.[google]'  # Installs both Google and OpenAI packages
   ```

### Memory Config Auto-Selection

The system automatically uses the right config:
- **LLM_PROVIDER=google** → Uses `config/mem0_google.json` (which uses OpenAI for Mem0)
- **LLM_PROVIDER=openai** → Uses `config/mem0_openai.json` (pure OpenAI)
- **LLM_PROVIDER=anthropic** → Uses `config/mem0_config.json` (fallback)

This hybrid approach is **transparent** - you set `LLM_PROVIDER=google` and everything works seamlessly!

## Using in Code

The framework automatically uses your configured provider:

```python
from core.llm import get_llm

# Get configured LLM
llm = get_llm()

# Or override provider
llm = get_llm(provider="google", model="gemini-2.0-flash-exp")

# Use with LangChain
response = llm.invoke("Analyze this Pokemon card data...")
```

## Context Window Comparison

| Provider | Model | Context Window | Best For |
|----------|-------|----------------|----------|
| Google | gemini-2.0-flash-exp | 2M tokens | Large datasets, extensive memory |
| Google | gemini-1.5-pro | 2M tokens | Production, reliability |
| OpenAI | gpt-4o-mini | 128K tokens | Cost-effective, structured output |
| OpenAI | gpt-4o | 128K tokens | Best reasoning |
| Anthropic | claude-3-5-sonnet | 200K tokens | Careful analysis |

**Token estimates for curators:**
- Pokemon card metadata: ~500 tokens per card
- API response (100 cards): ~50K tokens
- Memory context (strategic): ~10K tokens
- Collection structure: ~5K tokens

**With Gemini 2M context:**
- Can process 4,000+ cards in one request
- Maintain full conversation history
- Never lose context across runs

## Cost Comparison

**Processing 100,000 Pokemon cards:**

| Provider | Model | Cost |
|----------|-------|------|
| Google | gemini-2.0-flash-exp | $0 (free tier) |
| Google | gemini-1.5-pro | ~$3.75 |
| OpenAI | gpt-4o-mini | ~$7.50 |
| OpenAI | gpt-4o | ~$125 |
| Anthropic | claude-3-5-sonnet | ~$150 |

**Recommendation**: Start with Gemini free tier, upgrade to paid as needed.

## Memory Configuration

Memory (Mem0) automatically uses the right config for your provider:

```
config/
  mem0_google.json    # Used when LLM_PROVIDER=google
  mem0_openai.json    # Used when LLM_PROVIDER=openai
  mem0_config.json    # Custom/fallback
```

**Gemini advantages for memory:**
- Larger context = more memories in each query
- Cheaper = can query memories more often
- Faster = better real-time learning

## Switching Providers

You can switch at any time:

```bash
# Change in .env
LLM_PROVIDER=google

# Restart curator
curator run pokemon-tcg
```

**What carries over:**
- All database data (entities, relationships)
- Curator configuration
- Token budget tracking
- Rate limits

**What changes:**
- LLM API calls use new provider
- Memory config switches automatically
- Cost/context window characteristics

## Best Practices

### For Development
- **Use Gemini free tier**: Perfect for testing
- **Start with gpt-4o-mini**: If you prefer OpenAI
- **Prototype workflows cheaply**

### For Production
- **Gemini for data processing**: Large context, low cost
- **GPT-4o for decisions**: When you need best reasoning
- **Claude for safety**: Critical data validation

### Hybrid Approach
You can use different providers for different tasks:

```python
# Gemini for processing large datasets
data_llm = get_llm(provider="google", model="gemini-2.0-flash-exp")
cards = data_llm.invoke("Process this API response...")

# GPT-4o for critical decisions
decision_llm = get_llm(provider="openai", model="gpt-4o")
action = decision_llm.invoke("Should we import these cards?")
```

## Troubleshooting

### "Provider not installed"
```bash
pip install -e '.[google]'  # or openai, anthropic
```

### "API key not set"
Check `.env` has the right key:
```bash
GOOGLE_API_KEY=your-key-here  # Not OPENAI_API_KEY
```

### "Rate limit exceeded"
Gemini free tier: 1,500 requests/day
- Upgrade to paid tier
- Or add delays between requests

### "Context too long"
- Gemini: 2M tokens (rarely an issue)
- OpenAI: 128K tokens (might need chunking)
- Solution: Use Gemini for large contexts

## FAQ

**Q: Can I use different providers for LLM and embeddings?**
A: Currently they're paired, but you can manually override in code.

**Q: Which is best for Pokemon TCG?**
A: Gemini 2.0 Flash - huge context, free tier, perfect for processing API responses.

**Q: Can I switch mid-import?**
A: Yes, but that specific run will use one provider. Next run can use different one.

**Q: Does memory persist across provider changes?**
A: Yes! Memory is stored in Qdrant, provider-independent.

**Q: Which has best JSON output?**
A: OpenAI's structured outputs are currently the best, but Gemini is very good too.

## Recommended Setup

For most curator use cases:

```bash
# .env
LLM_PROVIDER=google
GOOGLE_API_KEY=your-key-here
GOOGLE_MODEL=gemini-2.0-flash-exp
```

**Why:**
- ✅ Free tier (1,500 requests/day)
- ✅ Massive 2M token context
- ✅ Fast processing
- ✅ Great for data-heavy tasks
- ✅ Can upgrade to paid seamlessly

You can always add other providers later for specific tasks!

---

**Next**: Try it out with Phase 2 Pokemon TCG curator 🎮
