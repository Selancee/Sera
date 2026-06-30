export default function DiffLegend() {
  return (
    <div className="diff-legend">
      <span><i className="diff-dot added" /> added</span>
      <span><i className="diff-dot removed" /> removed</span>
      <span><i className="diff-dot changed" /> changed</span>
      <span><i className="diff-dot ai" /> AI region</span>
    </div>
  );
}
