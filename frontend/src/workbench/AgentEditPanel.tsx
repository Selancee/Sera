const TOOLS = [
  "Rewrite selected measures",
  "Add variation",
  "Simplify selected passage",
  "Make more lyrical",
  "Make more dramatic",
  "Increase rhythmic density",
  "Decrease rhythmic density",
  "Add cadence",
  "Reharmonize selected range",
  "Generate left-hand accompaniment",
  "Fix validation warnings",
  "Explain selected passage"
];

type Constraints = Record<string, any>;

export default function AgentEditPanel({
  instruction,
  setInstruction,
  onAgentEdit,
  onExplain,
  disabled,
  constraints,
  onConstraintsChange,
  selectedRange
}: {
  instruction: string;
  setInstruction: (value: string) => void;
  onAgentEdit: (value?: string, constraints?: Constraints) => void;
  onExplain: (question?: string) => void;
  disabled: boolean;
  constraints: Constraints;
  onConstraintsChange: (value: Constraints) => void;
  selectedRange: Record<string, any>;
}) {
  function updateConstraint(key: string, value: any) {
    onConstraintsChange({ ...constraints, [key]: value });
  }

  function runTool(tool: string) {
    setInstruction(tool);
    if (tool === "Explain selected passage") {
      onExplain(tool);
      return;
    }
    onAgentEdit(tool, constraints);
  }

  return (
    <section className="workbench-panel">
      <div className="panel-heading tight">
        <h2>Agent Tools</h2>
        <span>M{selectedRange.start_measure}-{selectedRange.end_measure}</span>
      </div>
      <textarea rows={4} value={instruction} onChange={(event) => setInstruction(event.target.value)} />
      <div className="constraint-grid">
        {[
          ["preserve_melody", "Preserve melody"],
          ["preserve_harmony", "Preserve harmony"],
          ["preserve_rhythm", "Preserve rhythm"],
          ["preserve_form", "Preserve form"],
          ["keep_difficulty", "Keep difficulty"]
        ].map(([key, label]) => (
          <label key={key}>
            <input checked={Boolean(constraints[key])} onChange={(event) => updateConstraint(key, event.target.checked)} type="checkbox" />
            {label}
          </label>
        ))}
        <label>
          Difficulty
          <select value={constraints.target_difficulty || ""} onChange={(event) => updateConstraint("target_difficulty", event.target.value)}>
            <option value="">auto</option>
            <option value="beginner">beginner</option>
            <option value="intermediate">intermediate</option>
            <option value="advanced">advanced</option>
          </select>
        </label>
        <label>
          Patch size
          <select value={constraints.patch_size_limit || "small"} onChange={(event) => updateConstraint("patch_size_limit", event.target.value)}>
            <option value="small">small</option>
            <option value="medium">medium</option>
            <option value="large">large</option>
          </select>
        </label>
        <label>
          Staff
          <select value={constraints.target_staff || "both"} onChange={(event) => updateConstraint("target_staff", event.target.value)}>
            <option value="right_hand">right hand</option>
            <option value="left_hand">left hand</option>
            <option value="both">both</option>
          </select>
        </label>
        <label>
          Voice
          <select value={constraints.target_voice || "all"} onChange={(event) => updateConstraint("target_voice", event.target.value)}>
            <option value="1">voice 1</option>
            <option value="2">voice 2</option>
            <option value="all">all</option>
          </select>
        </label>
      </div>
      <div className="toolbar-row">
        <button disabled={disabled || !instruction.trim()} onClick={() => onAgentEdit(instruction, constraints)} type="button">Preview Agent Patch</button>
        <button disabled={disabled} onClick={() => onExplain(instruction)} type="button">Explain</button>
      </div>
      <div className="agent-tool-grid">
        {TOOLS.map((tool) => (
          <button disabled={disabled} key={tool} onClick={() => runTool(tool)} type="button">
            {tool}
          </button>
        ))}
      </div>
    </section>
  );
}
