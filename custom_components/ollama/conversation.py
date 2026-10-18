"""The conversation platform for the Ollama integration."""

import asyncio
import logging
import re
from typing import Any, Literal, override

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import OllamaConfigEntry
from .const import (
    CONF_ENABLE_GATEKEEPER,
    CONF_GATEKEEPER_HEURISTICS,
    CONF_GATEKEEPER_MODEL,
    CONF_GATEKEEPER_PROMPT,
    CONF_GATEKEEPER_SILENT,
    DEFAULT_ENABLE_GATEKEEPER,
    DEFAULT_GATEKEEPER_HEURISTICS,
    DEFAULT_GATEKEEPER_MODEL,
    DEFAULT_GATEKEEPER_PROMPT,
    DEFAULT_GATEKEEPER_SILENT,
    DOMAIN,
)
from .entity import OllamaBaseLLMEntity

_LOGGER = logging.getLogger(__name__)

COMMON_NOISE_FRAGMENTS = {
    "eh",
    "ah",
    "oh",
    "uh",
    "um",
    "mmm",
    "shh",
    "ay",
    "ey",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OllamaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up conversation entities."""
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "conversation":
            continue

        async_add_entities(
            [OllamaConversationEntity(config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class OllamaConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
    OllamaBaseLLMEntity,
):
    """Ollama conversation agent."""

    _attr_supports_streaming = True

    def __init__(self, entry: OllamaConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the agent."""
        super().__init__(entry, subentry)
        if self.subentry.data.get(CONF_LLM_HASS_API):
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )

    @override
    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    @override
    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    @property
    @override
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def _async_verify_gatekeeper(
        self, text: str, settings: dict[str, Any]
    ) -> bool:
        """Verify if user input is an intentional smart assistant request."""
        clean_text = (text or "").strip()
        if not clean_text:
            return False

        # Step 1: Immediate Heuristic Fast Filter (0ms)
        if settings.get(CONF_GATEKEEPER_HEURISTICS, DEFAULT_GATEKEEPER_HEURISTICS):
            clean_lower = re.sub(r"[^\w\s]", "", clean_text.lower()).strip()
            if (
                not clean_lower
                or clean_lower in COMMON_NOISE_FRAGMENTS
                or len(clean_lower) < 2
            ):
                return False

        # Step 2: Fast Pre-Flight Model Verification via Ollama AsyncClient
        client = self.entry.runtime_data
        model = settings.get(CONF_GATEKEEPER_MODEL, DEFAULT_GATEKEEPER_MODEL)
        system_prompt = settings.get(
            CONF_GATEKEEPER_PROMPT, DEFAULT_GATEKEEPER_PROMPT
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f'Frase: "{clean_text}"'},
        ]

        try:
            async with asyncio.timeout(3.0):
                res = await client.chat(
                    model=model,
                    messages=messages,
                    options={"temperature": 0.0, "num_predict": 3},
                )
                reply = (
                    res.get("message", {}).get("content") or ""
                ).strip().upper()
                return "SI" in reply
        except Exception as err:
            _LOGGER.warning(
                "Ollama Gatekeeper verification failed (%s), failing open", err
            )
            return True

    @override
    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Call the API."""
        settings = {**self.entry.data, **self.subentry.data}

        # Gatekeeper Pre-Flight Intent Verification
        if settings.get(CONF_ENABLE_GATEKEEPER, DEFAULT_ENABLE_GATEKEEPER):
            is_valid = await self._async_verify_gatekeeper(
                user_input.text, settings
            )
            if not is_valid:
                _LOGGER.info(
                    "🛡️ [Ollama Gatekeeper] Filtered accidental background utterance: '%s'",
                    user_input.text,
                )
                if settings.get(
                    CONF_GATEKEEPER_SILENT, DEFAULT_GATEKEEPER_SILENT
                ):
                    response = intent.IntentResponse(
                        language=user_input.language
                    )
                    response.response_type = (
                        intent.IntentResponseType.ACTION_DONE
                    )
                    return conversation.ConversationResult(
                        response=response,
                        conversation_id=user_input.conversation_id,
                    )

        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                settings.get(CONF_LLM_HASS_API),
                settings.get(CONF_PROMPT),
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        await self._async_handle_chat_log(chat_log)

        return conversation.async_get_result_from_chat_log(user_input, chat_log)
