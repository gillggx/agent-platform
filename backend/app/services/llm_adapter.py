from typing import List, Dict, Optional, Any
import asyncio
from dataclasses import dataclass
from app.core.config import settings
import litellm
import json
import re


@dataclass
class LLMUsage:
    """LLM usage statistics"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    provider: str


@dataclass
class LLMResponse:
    """LLM response wrapper"""
    content: str
    usage: LLMUsage
    model: str
    provider: str


class LLMAdapter:
    """Unified LLM interface using LiteLLM + OpenRouter"""
    
    def __init__(self):
        import os
        # Default model from config
        self.default_model = settings.llm_model
        # Set OPENROUTER_API_KEY for litellm to pick up
        if settings.llm_api_key and "openrouter" in settings.llm_provider.lower():
            os.environ["OPENROUTER_API_KEY"] = settings.llm_api_key
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        org_config: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Complete a chat conversation.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            model: Override model selection
            temperature: Response randomness (0.0-1.0)
            max_tokens: Maximum response tokens
            org_config: Organization LLM config — overrides api_key, model, provider (2.3.4)
        """
        # 2.3.4 — Resolve credentials: org_config first, fall back to global settings
        if org_config:
            api_key = org_config.get("api_key") or settings.llm_api_key
            model_name = model or org_config.get("model") or self.default_model
            provider = org_config.get("provider", settings.llm_provider)
        else:
            api_key = settings.llm_api_key
            model_name = model or self.default_model
            provider = settings.llm_provider

        if not api_key:
            raise Exception("LLM_API_KEY not set. Configure it in .env or org settings.")

        kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "api_key": api_key,
        }

        # 2.3.7 — Retry up to 3 attempts with per-call timeout; fail → session ERROR
        max_retries = 3
        call_timeout = 90  # seconds
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    litellm.acompletion(**kwargs),
                    timeout=call_timeout,
                )
                content = response.choices[0].message.content
                usage = LLMUsage(
                    prompt_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
                    total_tokens=getattr(response.usage, "total_tokens", 0) or 0,
                    model=response.model or model_name,
                    provider=provider,
                )
                return LLMResponse(
                    content=content,
                    usage=usage,
                    model=response.model or model_name,
                    provider=provider,
                )
            except asyncio.TimeoutError as e:
                last_error = e
                wait = 2 ** attempt
                print(f"LLM timeout (attempt {attempt}/{max_retries}), retrying in {wait}s...")
                await asyncio.sleep(wait)
            except Exception as e:
                err_str = str(e).lower()
                if "rate_limit" in err_str or "429" in err_str:
                    await self._handle_rate_limit(e)
                    last_error = e
                    continue
                raise Exception(f"LLM API error: {str(e)}")

        raise Exception(f"LLM call failed after {max_retries} attempts: {last_error}")
    
    async def _handle_rate_limit(self, error: Exception):
        """Handle rate limiting with exponential backoff"""
        wait_time = 10  # default 10 seconds
        
        error_str = str(error).lower()
        if "retry after" in error_str:
            try:
                match = re.search(r'retry after (\d+)', error_str)
                if match:
                    wait_time = int(match.group(1))
            except:
                pass
        
        print(f"Rate limited, waiting {wait_time} seconds...")
        await asyncio.sleep(wait_time)
    
    def get_default_model(self) -> str:
        """Get the default model"""
        return self.default_model
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token for English)"""
        return len(text) // 4
    
    async def test_connection(self) -> bool:
        """Test LLM connection with a simple request"""
        try:
            response = await self.complete(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
            )
            return response.content is not None
        except:
            return False


# Global instance
llm_adapter = LLMAdapter()
