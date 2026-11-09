"""LLM tools for the Abode AI Autonomy Steward companion integration.

Exposes the steward's configuration and charter to Home Assistant's LLM APIs
(so it is available to Assist and the MCP server) and provides a tool to ask
the App to run a reasoning pass on demand.

Implements the Home Assistant 2026.10.0+ LLM Tool API:
- tools subclass homeassistant.helpers.llm.Tool
- async_call returns homeassistant.helpers.llm.ToolResult
- tools declare their integration domain and annotations
"""

import probatio
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import (
    LLMContext,
    LLMTools,
    Tool,
    ToolAnnotations,
    ToolInput,
    ToolResult,
)

from .const import CONF_AI_TASK_ENTITY, CONF_NOTIFY_SERVICE, DOMAIN

CONFIG_ENTITY_ID = "sensor.abode_ai_autonomy_steward_config"
TRIGGER_EVENT = f"{DOMAIN}.trigger_reasoning"

CHARTER = """Abode AI Autonomy Steward is the continuous, goal-level reasoning layer (System 2) of this home.

It subscribes to Home Assistant's event stream and wakes only when something changes. On each pass it pulls the complete current state fresh, decides whether any action is warranted, and either:
- executes an already-approved kind of action if this specific moment calls for it,
- proposes a new kind of action via mobile notification (Approve / Deny / Never),
- proposes replacing an already-approved kind of action.

Every proposed action is checked against an append-only constraint layer before execution. Tapping "Never" permanently appends a new constraint; constraints can only be removed by editing constraints.yaml directly.

Boundaries include: never disable safety alarms or alarm arming state, never unlock in a way that could trap or lock out a resident without an explicit action_type covering the scenario, never cast inappropriate content to shared screens, never make the whole home maximally visible/audible at night without evidence of an intruder or emergency, and never propose costly or irreversible actions without flagging them explicitly."""


class GetConfigurationTool(Tool):
    """Return the steward's current configuration."""

    name = f"{DOMAIN}__get_configuration"
    title = "Get Abode AI Autonomy Steward configuration"
    description = (
        "Returns the notify service and AI Task entity currently configured "
        "for the Abode AI Autonomy Steward. Use this when you need to know "
        "which notification service and AI Task entity the steward is using."
    )
    integration = DOMAIN
    annotations = ToolAnnotations(
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    )
    parameters = probatio.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: ToolInput,
        llm_context: LLMContext,
    ) -> ToolResult:
        """Return the current steward configuration."""
        state = hass.states.get(CONFIG_ENTITY_ID)
        attrs = state.attributes if state else {}
        return ToolResult(
            data={
                CONF_NOTIFY_SERVICE: attrs.get(CONF_NOTIFY_SERVICE),
                CONF_AI_TASK_ENTITY: attrs.get(CONF_AI_TASK_ENTITY),
            }
        )


class ExplainCharterTool(Tool):
    """Return the steward's charter and boundaries."""

    name = f"{DOMAIN}__explain_charter"
    title = "Explain Abode AI Autonomy Steward charter"
    description = (
        "Returns the charter, boundaries, and approval protocol of the "
        "Abode AI Autonomy Steward. Use this when asked how the steward "
        "decides what to do, what it can and cannot control, or how "
        "approvals and constraints work."
    )
    integration = DOMAIN
    annotations = ToolAnnotations(
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    )
    parameters = probatio.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: ToolInput,
        llm_context: LLMContext,
    ) -> ToolResult:
        """Return the steward charter."""
        return ToolResult(data={"charter": CHARTER})


class TriggerReasoningTool(Tool):
    """Ask the steward App to run a reasoning pass."""

    name = f"{DOMAIN}__trigger_reasoning"
    title = "Trigger Abode AI Autonomy Steward reasoning"
    description = (
        "Asks the Abode AI Autonomy Steward App to wake and run a reasoning "
        "pass immediately. Use this when the user wants the steward to "
        "re-evaluate the current state and decide whether to propose or "
        "execute an action."
    )
    integration = DOMAIN
    annotations = ToolAnnotations(
        read_only=False,
        destructive=False,
        idempotent=True,
        open_world=False,
    )
    parameters = probatio.Schema({})

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: ToolInput,
        llm_context: LLMContext,
    ) -> ToolResult:
        """Fire an event the App listens for."""
        hass.bus.fire(TRIGGER_EVENT, {"source": "llm_tool"})
        return ToolResult(
            data={"triggered": True, "event": TRIGGER_EVENT}
        )


@callback
def async_get_tools(
    hass: HomeAssistant,
    llm_context: LLMContext,
    api_id: str,
) -> LLMTools | None:
    """Return the tools for this integration.

    Tools are offered to the Assist API and any custom LLM API that
    requests them.
    """
    return LLMTools(
        tools=[
            GetConfigurationTool(),
            ExplainCharterTool(),
            TriggerReasoningTool(),
        ],
        prompt=(
            "The Abode AI Autonomy Steward is a separate Supervisor-managed "
            "App that reasons about the home's state and proposes autonomous "
            "actions subject to human approval and an append-only constraint "
            "layer. Use its tools to inspect its configuration, understand "
            "its charter, or ask it to re-evaluate the home state."
        ),
    )
