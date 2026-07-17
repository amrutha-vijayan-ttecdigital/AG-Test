"""Data models for the CES semantic Design IR (ces-design-ir/v1)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, List, Dict, Optional

# Version string
SCHEMA_VERSION = "ces-design-ir/v1"

class Modality(str, Enum):
    MUST = "MUST"
    MAY = "MAY"
    MUST_NOT = "MUST_NOT"
    SHOULD = "SHOULD"
    SHOULD_NOT = "SHOULD_NOT"

class ControlAuthority(str, Enum):
    MODEL_INSTRUCTION = "MODEL_INSTRUCTION"
    DETERMINISTIC_HANDOFF_RULE = "DETERMINISTIC_HANDOFF_RULE"
    CALLBACK = "CALLBACK"
    GUARDRAIL = "GUARDRAIL"
    TOOL_IMPLEMENTATION = "TOOL_IMPLEMENTATION"
    REMOTE_DIALOGFLOW_AGENT = "REMOTE_DIALOGFLOW_AGENT"
    CLIENT_APPLICATION = "CLIENT_APPLICATION"
    HUMAN_PROCESS = "HUMAN_PROCESS"
    PLATFORM_RUNTIME = "PLATFORM_RUNTIME"
    OBSERVED_ONLY = "OBSERVED_ONLY"
    UNKNOWN = "UNKNOWN"

class RelationshipType(str, Enum):
    PARENT_OF = "PARENT_OF"
    MAY_HANDOFF_TO = "MAY_HANDOFF_TO"
    MUST_HANDOFF_TO = "MUST_HANDOFF_TO"
    BLOCKS_HANDOFF_TO = "BLOCKS_HANDOFF_TO"
    RETURNS_TO = "RETURNS_TO"
    CALLS_TOOL = "CALLS_TOOL"
    USES_AGENT_AS_TOOL = "USES_AGENT_AS_TOOL"
    GUARDED_BY = "GUARDED_BY"
    ENFORCED_BY = "ENFORCED_BY"
    READS_VARIABLE = "READS_VARIABLE"
    WRITES_VARIABLE = "WRITES_VARIABLE"
    ESCALATES_TO_HUMAN = "ESCALATES_TO_HUMAN"
    INVOKES_REMOTE_FLOW_AGENT = "INVOKES_REMOTE_FLOW_AGENT"
    PRODUCES_OUTPUT = "PRODUCES_OUTPUT"
    CONSUMES_INPUT = "CONSUMES_INPUT"
    OBSERVED_TRANSITION = "OBSERVED_TRANSITION"
    FORBIDDEN_TRANSITION = "FORBIDDEN_TRANSITION"

class CallbackStage(str, Enum):
    BEFORE_AGENT = "before_agent_callback"
    AFTER_AGENT = "after_agent_callback"
    BEFORE_MODEL = "before_model_callback"
    AFTER_MODEL = "after_model_callback"
    BEFORE_TOOL = "before_tool_callback"
    AFTER_TOOL = "after_tool_callback"

class GuardrailOutcome(str, Enum):
    EXACT_RESPONSE = "exact_response"
    GENERATED_RESPONSE = "generated_response"
    AGENT_HANDOFF = "agent_handoff"
    BLOCK = "block"
    REDACT = "redact"
    OTHER = "other"

class AsyncState(str, Enum):
    IDLE = "IDLE"
    REQUESTED = "REQUESTED"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"

@dataclass
class SourceProvenance:
    documentId: str = ""
    pageId: str = ""
    shapeIds: List[str] = field(default_factory=list)
    lineIds: List[str] = field(default_factory=list)
    textAreaIds: List[str] = field(default_factory=list)
    customDataKeys: List[str] = field(default_factory=list)

@dataclass
class EvidenceSpec:
    kind: str = ""  # custom_data, structured_label, shape_text, etc.
    value: str = ""
    confidence: float = 1.0

@dataclass
class BaseResource:
    id: str
    displayName: str
    source: SourceProvenance = field(default_factory=SourceProvenance)
    evidence: List[EvidenceSpec] = field(default_factory=list)
    status: str = "explicit"  # explicit, inferred, ambiguous, observed, deprecated
    unknown_fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ApplicationSpec(BaseResource):
    rootAgentId: str = ""
    globalInstructionRefs: List[str] = field(default_factory=list)
    defaultModelSettings: Dict[str, Any] = field(default_factory=dict)
    toolExecutionMode: str = "unspecified"  # parallel, sequential, unspecified
    channelProfiles: List[str] = field(default_factory=list)
    languageLocale: str = ""
    variableDeclarations: List[str] = field(default_factory=list)
    loggingRedactionRequirements: str = ""
    evaluationThresholdRefs: List[str] = field(default_factory=list)
    humanEscalationTargets: List[str] = field(default_factory=list)

@dataclass
class AgentSpec(BaseResource):
    kind: str = "llm_agent"  # llm_agent, remote_dialogflow_agent, human_handoff_target, external_agent
    parentAgentId: Optional[str] = None
    childAgentIds: List[str] = field(default_factory=list)
    isRoot: bool = False
    purpose: str = ""
    inScopeGoals: List[str] = field(default_factory=list)
    outOfScopeGoals: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    entryAssumptions: List[str] = field(default_factory=list)
    completionCriteria: List[str] = field(default_factory=list)
    handoffCriteria: List[str] = field(default_factory=list)
    attachedTools: List[str] = field(default_factory=list)
    attachedAgentsAsTools: List[str] = field(default_factory=list)
    callbacks: List[str] = field(default_factory=list)
    guardrails: List[str] = field(default_factory=list)
    variablesRead: List[str] = field(default_factory=list)
    variablesWritten: List[str] = field(default_factory=list)
    modelOverride: Optional[str] = None
    channelInstructionRefs: List[str] = field(default_factory=list)
    humanEscalationBehavior: str = ""

@dataclass
class BehavioralClaim(BaseResource):
    subjectId: str = ""
    modality: Modality = Modality.MAY
    predicate: str = ""
    scope: str = ""
    preconditions: List[str] = field(default_factory=list)
    enforcementAuthority: Optional[str] = None  # callback, guardrail, platform
    enforcementResourceId: Optional[str] = None
    failureBehavior: str = ""

@dataclass
class RelationshipSpec(BaseResource):
    sourceId: str = ""
    targetId: str = ""
    relationType: RelationshipType = RelationshipType.PARENT_OF
    modalGuarantee: Modality = Modality.MAY
    controlAuthority: ControlAuthority = ControlAuthority.UNKNOWN
    triggerCondition: str = ""
    ownershipSemantics: str = ""  # transfer, retain, delegate
    returnBehavior: str = ""
    syncBehavior: str = "synchronous"  # synchronous, asynchronous
    failureTimeoutBehavior: str = ""
    confidence: float = 1.0

@dataclass
class HandoffSpec(BaseResource):
    sourceAgentId: str = ""
    targetAgentId: str = ""
    direction: str = ""  # forward, backward, lateral, human
    mechanism: str = "unknown"  # model_instruction, deterministic_handoff_rule, callback, guardrail, client
    forceBlockBehavior: str = ""  # force, block, none
    condition: str = ""
    requiredVariables: List[str] = field(default_factory=list)
    dataPassed: List[str] = field(default_factory=list)
    postTransferOwner: str = ""
    returnCondition: str = ""
    returnTargetAgentId: Optional[str] = None
    retryLoopPolicy: str = ""
    failureBehavior: str = ""

@dataclass
class AgentAsToolSpec(BaseResource):
    callingAgentId: str = ""
    targetAgentId: str = ""
    toolName: str = ""
    description: str = ""
    inputContract: str = ""
    outputContract: str = ""
    executionType: str = "synchronous"
    pendingResponseBehavior: str = ""
    duplicatePolicy: str = ""
    timeoutCancellation: str = ""
    resultsCommunication: str = ""

@dataclass
class ToolSpec(BaseResource):
    toolKind: str = ""
    description: str = ""
    agents: List[str] = field(default_factory=list)
    inputSchema: Optional[Dict[str, Any]] = None
    outputSchema: Optional[Dict[str, Any]] = None
    executionType: str = "unknown"  # synchronous, asynchronous, client-executed, unknown
    sideEffectClass: str = "unknown"  # read-only, reversible_write, irreversible_write, unknown
    authRequirement: str = ""
    confirmationRequirement: bool = False
    idempotencyStrategy: str = ""
    timeoutRetryPolicy: str = ""
    pendingResponseContract: str = ""
    errorResultContract: str = ""
    sensitiveData: List[str] = field(default_factory=list)
    callbacks: List[str] = field(default_factory=list)
    mockStrategy: str = ""

@dataclass
class CallbackSpec(BaseResource):
    callbackStage: CallbackStage = CallbackStage.BEFORE_AGENT
    scope: str = ""
    purpose: str = ""
    variablesRead: List[str] = field(default_factory=list)
    variablesWritten: List[str] = field(default_factory=list)
    skipReplaceBehavior: str = ""
    validationBehavior: str = ""
    authBehavior: str = ""
    modificationBehavior: str = ""
    orderingIndex: int = 0
    failureBehavior: str = ""
    codeRef: str = ""

@dataclass
class GuardrailSpec(BaseResource):
    kind: str = ""  # prompt_guard, blocklist, safety, code_rule, etc.
    scope: str = ""  # input, output, both
    triggerDefinition: str = ""
    outcome: GuardrailOutcome = GuardrailOutcome.OTHER
    outcomeTarget: str = ""
    severity: str = ""
    variablesCaptured: List[str] = field(default_factory=list)

@dataclass
class VariableSpec(BaseResource):
    type: str = ""
    classification: str = "dynamic"  # static, dynamic
    ownerAgentId: Optional[str] = None
    readers: List[str] = field(default_factory=list)
    writers: List[str] = field(default_factory=list)
    sourceOfTruth: str = ""
    defaultValue: Optional[Any] = None
    sessionLifetime: str = ""
    sensitivity: str = ""  # pii, sensitive, public
    validationRules: List[str] = field(default_factory=list)
    redactionExpectations: str = ""
    remoteMappings: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RemoteDialogflowAgentRef(BaseResource):
    remoteAgentResource: str = ""
    startingFlow: str = ""
    environmentVersion: str = ""
    inputVariables: List[str] = field(default_factory=list)
    outputVariables: List[str] = field(default_factory=list)
    languageCodeVariable: str = ""
    ownershipSemantics: str = ""
    returnBehavior: str = ""
    errorTimeoutBehavior: str = ""

@dataclass
class ChannelProfileSpec(BaseResource):
    channelType: str = ""
    promptRef: str = ""
    bargeInExpectations: str = ""
    mandatoryMessages: List[str] = field(default_factory=list)
    inactivityBehavior: str = ""
    asyncToolBehavior: str = ""
    evaluationReferences: List[str] = field(default_factory=list)
    errorReconnectBehavior: str = ""

@dataclass
class EvaluationSpec(BaseResource):
    description: str = ""
    startingAgentId: str = ""
    userGoal: str = ""
    initialVariables: Dict[str, Any] = field(default_factory=dict)
    must: List[str] = field(default_factory=list)
    may: List[str] = field(default_factory=list)
    mustNot: List[str] = field(default_factory=list)
    expectedToolCalls: List[Dict[str, Any]] = field(default_factory=list)
    expectedHandoffs: List[Dict[str, Any]] = field(default_factory=list)
    expectedOutcome: Dict[str, Any] = field(default_factory=dict)
    toolFakes: List[Dict[str, Any]] = field(default_factory=list)
    channel: str = "text"
    runMode: str = "golden"
    repeatedTrials: int = 1
    passCriteria: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ObservedTrace(BaseResource):
    appVersion: str = ""
    orderedSpans: List[Dict[str, Any]] = field(default_factory=list)
    toolCalls: List[Dict[str, Any]] = field(default_factory=list)
    agentTransfers: List[Dict[str, Any]] = field(default_factory=list)
    latencyMs: int = 0
    errors: List[str] = field(default_factory=list)
    finalOutcome: str = ""
    designResourceLinks: List[str] = field(default_factory=list)
