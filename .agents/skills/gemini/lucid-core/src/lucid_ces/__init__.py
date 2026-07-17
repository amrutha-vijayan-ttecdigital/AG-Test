"""Public API for the Lucid CES compiler package."""

from .errors import (
    LucidCesError,
    LucidCesParseError,
    LucidCesCompileError,
    LucidCesValidationError,
    LucidCesDiffError
)

from .models import (
    SCHEMA_VERSION,
    Modality,
    ControlAuthority,
    RelationshipType,
    CallbackStage,
    GuardrailOutcome,
    AsyncState,
    SourceProvenance,
    EvidenceSpec,
    BaseResource,
    ApplicationSpec,
    AgentSpec,
    BehavioralClaim,
    RelationshipSpec,
    HandoffSpec,
    AgentAsToolSpec,
    ToolSpec,
    CallbackSpec,
    GuardrailSpec,
    VariableSpec,
    RemoteDialogflowAgentRef,
    ChannelProfileSpec,
    EvaluationSpec,
    ObservedTrace
)

from .serialization import (
    from_dict,
    to_dict,
    load_json,
    write_json_atomic
)

from .lucid_adapter import (
    load_lucid_graph
)

from .metadata import (
    parse_visible_label,
    get_ces_custom_data
)

from .classify import (
    classify_shape
)

from .compile import (
    compile_design
)

from .relationships import (
    CesDesignQuery
)

from .validate import (
    CesValidator
)

from .runtime_ces import (
    load_saved_runtime_export
)

from .diff import (
    diff_design_and_runtime,
    render_diff_markdown
)

from .evaluations import (
    generate_eval_specs_from_design,
    render_evals_mapping_guide
)

from .context_packet import (
    generate_context_packet
)

from .render_markdown import (
    render_markdown_report
)

from .render_mermaid import (
    render_mermaid_diagram
)
